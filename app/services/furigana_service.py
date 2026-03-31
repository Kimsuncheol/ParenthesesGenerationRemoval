import re

import jaconv
import pykakasi
import cutlet

_kks = pykakasi.kakasi()
_katsu = cutlet.Cutlet(use_foreign_spelling=False)

# Rendaku (consonant voicing): maps unvoiced → voiced kana
_RENDAKU = str.maketrans(
    "かきくけこさしすせそたちつてとはひふへほ",
    "がぎぐげござじずぜぞだぢづでどばびぶべぼ",
)
_HANDAKU = str.maketrans("はひふへほ", "ぱぴぷぺぽ")
_EMPTY_PARENS_RE = re.compile(r"\(\)")
_READING_PARENS_RE = re.compile(r"\([^)]*\)")

# Surface-level overrides for known unidic-lite misreadings
_KANA_EXCEPTIONS: dict[str, str] = {
    "丸い": "まるい",
    "温く": "ぬるく",
}


def _is_kanji(char: str) -> bool:
    cp = ord(char)
    return 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF


def _pykakasi_hira(char: str) -> str:
    """Return pykakasi's hiragana reading for a single character."""
    result = _kks.convert(char)
    return result[0]["hira"] if result else char


def _single_char_hira(char: str) -> str | None:
    """Return a single-character reading from MeCab when available."""
    tokens = _katsu.tagger(char)
    if len(tokens) != 1:
        return None

    kana = getattr(tokens[0].feature, "kana", None)
    if not kana:
        return None

    return jaconv.kata2hira(kana)


def _reading_hints(char: str) -> list[str]:
    """Collect likely readings for a single character."""
    hints: list[str] = []
    for candidate in (_single_char_hira(char), _pykakasi_hira(char)):
        if candidate and candidate not in hints:
            hints.append(candidate)
    return hints


def _reading_variants(hint: str) -> list[str]:
    """Expand a base hint with voiced and semi-voiced variants."""
    variants: list[str] = []
    for candidate in (hint, hint.translate(_RENDAKU), hint.translate(_HANDAKU)):
        if candidate and candidate not in variants:
            variants.append(candidate)
    return variants


def _split_kanji_reading(chars: list[str], reading: str) -> list[str] | None:
    """
    Try to distribute `reading` across individual kanji in `chars`.

    Returns a list of per-character readings if successful, or None to fall
    back to compound annotation (e.g. 今年(ことし)).

    Strategy for 2 kanji: right-anchor first (pykakasi hint for chars[1]),
    then left-anchor (pykakasi hint for chars[0]).  Rendaku variants are
    tried for each.  Right-anchor is tried first because the final kanji's
    reading in a compound is the most stable anchor point.

    Strategy for 3+ kanji: left-greedy with pykakasi hints.
    """
    n = len(chars)
    if n == 0:
        return []
    if n == 1:
        return [reading]

    if n == 2:
        for hint2 in _reading_hints(chars[1]):
            for candidate in _reading_variants(hint2):
                if candidate and reading.endswith(candidate) and len(reading) > len(candidate):
                    return [reading[: -len(candidate)], reading[-len(candidate) :]]

        for hint1 in _reading_hints(chars[0]):
            for candidate in _reading_variants(hint1):
                if candidate and reading.startswith(candidate) and len(reading) > len(candidate):
                    return [reading[: len(candidate)], reading[len(candidate) :]]

        return None

    # 3+ kanji: left-greedy
    parts: list[str] = []
    remaining = reading
    for ch in chars[:-1]:
        matched = False
        for hint in _reading_hints(ch):
            for candidate in _reading_variants(hint):
                if candidate and remaining.startswith(candidate) and len(remaining) > len(candidate):
                    parts.append(candidate)
                    remaining = remaining[len(candidate) :]
                    matched = True
                    break
            if matched:
                break
        if not matched:
            return None
    parts.append(remaining)
    return parts


def _consume_parenthesized_reading(text: str, start: int) -> tuple[str, int] | None:
    """Return the direct '(reading)' span that starts at `start`, if present."""
    if start >= len(text) or text[start] != "(":
        return None

    end = text.find(")", start + 1)
    if end == -1:
        return None

    return text[start + 1 : end], end + 1


def _placeholder_skeleton(annotated: str) -> str:
    """Replace furigana contents with empty placeholders."""
    return _READING_PARENS_RE.sub("()", annotated)


def _raw_placeholder_skeleton(surface: str) -> str:
    """Generate the empty-placeholder shape for a surface token."""
    return "".join(f"{char}()" if _is_kanji(char) else char for char in surface)


def _align_reading(segments: list[tuple[bool, str]], reading: str) -> str | None:
    """
    Distribute `reading` across interleaved (is_kanji, text) segments.

    Non-kanji segments act as anchors: their characters are consumed from
    `reading` in order, allowing each kanji block's reading to be isolated.
    Returns the annotated string, or None on alignment failure.
    """
    result: list[str] = []
    remaining = reading

    for idx, (is_k, text) in enumerate(segments):
        if not is_k:
            # Non-kanji: must match the next chars in the remaining reading
            if remaining.startswith(text):
                result.append(text)
                remaining = remaining[len(text):]
            else:
                return None
        else:
            # Kanji block: find reading by looking at the next non-kanji anchor
            next_kana: str | None = None
            for j in range(idx + 1, len(segments)):
                if not segments[j][0]:
                    next_kana = segments[j][1]
                    break

            if next_kana is not None:
                pos = remaining.find(next_kana)
                if pos <= 0:
                    return None
                kanji_reading = remaining[:pos]
                remaining = remaining[pos:]
            else:
                kanji_reading = remaining
                remaining = ""

            if not kanji_reading:
                return None

            split = _split_kanji_reading(list(text), kanji_reading)
            if split:
                result.append("".join(f"{c}({r})" for c, r in zip(text, split)))
            else:
                result.append(f"{text}({kanji_reading})")

    return "".join(result)


def _annotate_token(surface: str, hira: str) -> str:
    """
    Add furigana to the kanji portion of a single MeCab token.

    Splits the surface into alternating kanji/non-kanji segments, strips the
    outer prefix and suffix from the reading, then aligns the remaining
    reading with each segment using non-kanji chars as anchors.

    This correctly handles interleaved patterns like 飲み物 (の + み + もの)
    as well as simple cases like 冷たい (つめ + たい stripped as suffix).
    """
    # Split surface into alternating (is_kanji, text) segments
    segments: list[tuple[bool, str]] = []
    i = 0
    while i < len(surface):
        is_k = _is_kanji(surface[i])
        j = i + 1
        while j < len(surface) and _is_kanji(surface[j]) == is_k:
            j += 1
        segments.append((is_k, surface[i:j]))
        i = j

    if not any(is_k for is_k, _ in segments):
        return surface

    reading = hira

    # Strip outer non-kanji prefix from reading
    prefix = ""
    if segments and not segments[0][0]:
        candidate = segments[0][1]
        if reading.startswith(candidate):
            prefix = candidate
            reading = reading[len(candidate):]
            segments = segments[1:]

    # Strip outer non-kanji suffix (okurigana) from reading
    suffix = ""
    if segments and not segments[-1][0]:
        candidate = segments[-1][1]
        if reading.endswith(candidate):
            suffix = candidate
            reading = reading[:-len(candidate)]
            segments = segments[:-1]

    if not reading or not segments:
        return surface

    annotated = _align_reading(segments, reading)
    if annotated is None:
        return surface

    return prefix + annotated + suffix


def add_furigana(text: str) -> str:
    """Annotate each kanji in `text` with its hiragana reading in parentheses.

    Kanji that are already followed by a parenthesised reading in the input
    (e.g. 旅行(りょこう)) are normalized to per-kanji furigana when possible.
    """
    source_text = _EMPTY_PARENS_RE.sub("", text)
    result: list[str] = []
    cursor = 0
    source_cursor = 0

    for token in _katsu.tagger(source_text):
        surface: str = token.surface
        ws: str = token.white_space
        if ws and source_text.startswith(ws, source_cursor):
            result.append(ws)
            cursor += len(ws)
            source_cursor += len(ws)

        if not source_text.startswith(surface, source_cursor):
            continue

        token_end = source_cursor + len(surface)
        has_kanji = any(_is_kanji(c) for c in surface)

        if not has_kanji:
            result.append(surface)
            cursor += len(surface)
            source_cursor = token_end
            continue

        kana = getattr(token.feature, "kana", None)
        if token.is_unk or not kana:
            result.append(surface)
            cursor += len(surface)
            source_cursor = token_end
            continue

        hira = _KANA_EXCEPTIONS.get(surface) or jaconv.kata2hira(kana)
        annotated = _annotate_token(surface, hira)
        placeholder_skeleton = _placeholder_skeleton(annotated)
        raw_placeholder = _raw_placeholder_skeleton(surface)

        if text.startswith(placeholder_skeleton, cursor):
            result.append(annotated)
            cursor += len(placeholder_skeleton)
            source_cursor = token_end
            continue

        if raw_placeholder != placeholder_skeleton and text.startswith(raw_placeholder, cursor):
            result.append(annotated)
            cursor += len(raw_placeholder)
            source_cursor = token_end
            continue

        existing_reading = None
        if text.startswith(surface, cursor):
            existing_reading = _consume_parenthesized_reading(text, cursor + len(surface))
        if existing_reading is not None:
            raw_reading, annotated_end = existing_reading
            source_reading = _consume_parenthesized_reading(source_text, token_end)
            hira = jaconv.kata2hira(raw_reading)
            normalized = _annotate_token(surface, hira)
            if normalized != f"{surface}({hira})":
                result.append(normalized)
            else:
                result.append(surface + text[cursor + len(surface):annotated_end])
            cursor = annotated_end
            source_cursor = source_reading[1] if source_reading is not None else token_end
            continue

        result.append(annotated)
        cursor += len(surface)
        source_cursor = token_end

    if cursor < len(text):
        result.append(text[cursor:])

    return "".join(result)
