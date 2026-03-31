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
        hint2 = _pykakasi_hira(chars[1])
        for candidate in (hint2, hint2.translate(_RENDAKU)):
            if candidate and reading.endswith(candidate) and len(reading) > len(candidate):
                return [reading[: -len(candidate)], reading[-len(candidate) :]]
        hint1 = _pykakasi_hira(chars[0])
        for candidate in (hint1, hint1.translate(_RENDAKU)):
            if candidate and reading.startswith(candidate) and len(reading) > len(candidate):
                return [reading[: len(candidate)], reading[len(candidate) :]]
        return None

    # 3+ kanji: left-greedy
    parts: list[str] = []
    remaining = reading
    for ch in chars[:-1]:
        hint = _pykakasi_hira(ch)
        matched = False
        for candidate in (hint, hint.translate(_RENDAKU)):
            if candidate and remaining.startswith(candidate) and len(remaining) > len(candidate):
                parts.append(candidate)
                remaining = remaining[len(candidate) :]
                matched = True
                break
        if not matched:
            return None
    parts.append(remaining)
    return parts


def _annotate_token(surface: str, hira: str) -> str:
    """
    Add furigana to the kanji portion of a single MeCab token.

    Strips leading non-kanji (prefix) and trailing non-kanji (okurigana)
    from both the surface and the reading, then annotates the kanji block.
    """
    # Locate the kanji block
    i = 0
    while i < len(surface) and not _is_kanji(surface[i]):
        i += 1
    prefix = surface[:i]
    j = i
    while j < len(surface) and _is_kanji(surface[j]):
        j += 1
    kanji_block = surface[i:j]
    okurigana = surface[j:]

    if not kanji_block:
        return surface

    # Extract the kanji-only reading
    kanji_reading = hira
    if prefix and kanji_reading.startswith(prefix):
        kanji_reading = kanji_reading[len(prefix) :]
    if okurigana and kanji_reading.endswith(okurigana):
        kanji_reading = kanji_reading[: -len(okurigana)]

    if not kanji_reading:
        return surface

    split = _split_kanji_reading(list(kanji_block), kanji_reading)
    if split:
        annotated = "".join(f"{c}({r})" for c, r in zip(kanji_block, split))
    else:
        annotated = f"{kanji_block}({kanji_reading})"

    return prefix + annotated + okurigana


def add_furigana(text: str) -> str:
    """Annotate each kanji in `text` with its hiragana reading in parentheses."""
    result: list[str] = []
    for token in _katsu.tagger(text):
        surface: str = token.surface
        ws: str = token.white_space

        if not any(_is_kanji(c) for c in surface):
            result.append(ws + surface)
            continue

        kana = getattr(token.feature, "kana", None)
        if token.is_unk or not kana:
            result.append(ws + surface)
            continue

        hira = _KANA_EXCEPTIONS.get(surface) or jaconv.kata2hira(kana)
        result.append(ws + _annotate_token(surface, hira))

    return "".join(result)
