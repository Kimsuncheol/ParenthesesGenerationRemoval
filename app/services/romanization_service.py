import re

import cutlet
from korean_romanizer.romanizer import Romanizer
import pykakasi

# --- pykakasi: used for hiragana/katakana-only input (no kanji) ---
_kks = pykakasi.kakasi()

# --- cutlet: used for mixed or kanji-containing input ---
# use_wa:  は → wa (topic particle)
# use_wo:  を → o  (object particle, modified Hepburn)
# use_he:  へ → e  (direction particle)
# use_foreign_spelling: off — keep Japanese-based romanization
_katsu = cutlet.Cutlet(use_foreign_spelling=False)
_katsu.use_wa = True
_katsu.use_wo = False
_katsu.use_he = False

# Override unidic-lite readings that differ from common everyday readings
_EXCEPTIONS: dict[str, str] = {
    "私": "watashi",    # unidic-lite prefers formal 'watakushi'
    "日本": "Nihon",    # unidic-lite prefers 'nippon'
    "明日": "ashita",   # unidic-lite prefers literary 'asu'
    "今日": "kyou",     # unidic-lite may prefer 'konnichi'
    "中国": "chuugoku", # prevent proper-noun capitalization
}
for surface, reading in _EXCEPTIONS.items():
    _katsu.add_exception(surface, reading)

_KANJI_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

# Proper-noun compounds that MeCab splits but should be merged in romaji.
# Each entry is (pattern_to_find, replacement).
_MERGE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bChuugoku go\b", re.IGNORECASE), "chuugokugo"),
]


def _has_kanji(text: str) -> bool:
    return bool(_KANJI_RE.search(text))


def romanize_ja(text: str) -> str:
    """Convert Japanese text to Hepburn romanization.

    - For hiragana/katakana-only text: returns lowercase with no extra spaces.
    - For text containing kanji: returns sentence-case with word spacing.
    """
    if _has_kanji(text):
        result = _katsu.romaji(text)
        # Remove Hepburn disambiguation apostrophes (kon'ya → konya)
        result = re.sub(r"n'([aeiouy])", r"n\1", result)
        # Merge compounds that MeCab incorrectly splits
        for pattern, replacement in _MERGE_PATTERNS:
            result = pattern.sub(replacement, result)
    else:
        result = "".join(item["hepburn"] or item["orig"] for item in _kks.convert(text))
    return result


def romanize_ko(text: str) -> str:
    """Convert Korean Hangul text to revised romanization."""
    return Romanizer(text).romanize()
