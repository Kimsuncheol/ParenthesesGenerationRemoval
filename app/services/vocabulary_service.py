import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import jaconv

from app.models.text_models import VocabularyEntry
from app.services import romanization_service

VOCABULARY_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "vocabulary_entries.json"
_MAX_MEANINGS = 5
_JAPANESE_TEXT_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\u31f0-\u31ff々ー]")


@dataclass(frozen=True)
class _DictionaryEntry:
    word: str | None
    reading: str | None
    meanings: tuple[str, ...]
    part_of_speech: tuple[str, ...]
    is_common: bool
    normalized_word: str | None
    normalized_reading: str | None
    normalized_forms: tuple[str, ...]


def lookup_vocabulary(text: str) -> VocabularyEntry | None:
    raw_query = text.strip()
    normalized = _normalize_lookup_text(text)
    if not normalized or not _contains_japanese(text):
        return None

    candidates: list[tuple[int, int, int, _DictionaryEntry]] = []
    for entry in _load_dictionary():
        match_rank = _match_rank(entry, raw_query, normalized)
        if match_rank == 0:
            continue
        candidates.append(
            (
                match_rank,
                int(entry.is_common),
                -len(entry.meanings),
                entry,
            )
        )

    if not candidates:
        return None

    best_entry = max(
        candidates,
        key=lambda item: (
            item[0],
            item[1],
            item[2],
            item[3].word or "",
            item[3].reading or "",
        ),
    )[3]

    reading = best_entry.reading
    romanized = romanization_service.romanize_ja(reading) if reading else None
    return VocabularyEntry(
        word=best_entry.word,
        reading=reading,
        romanized=romanized,
        meanings=list(best_entry.meanings[:_MAX_MEANINGS]),
        part_of_speech=list(best_entry.part_of_speech),
        is_common=best_entry.is_common,
    )


def _contains_japanese(text: str) -> bool:
    return bool(_JAPANESE_TEXT_RE.search(text))


def _match_rank(entry: _DictionaryEntry, raw_text: str, normalized_text: str) -> int:
    if entry.word and entry.word == raw_text:
        return 3
    if entry.reading and entry.reading == raw_text:
        return 2
    if normalized_text in entry.normalized_forms:
        return 1
    return 0


def _normalize_lookup_text(text: str) -> str:
    normalized = jaconv.normalize(text.strip(), "NFKC")
    normalized = normalized.replace(" ", "").replace("　", "")
    return jaconv.kata2hira(normalized)


@lru_cache(maxsize=1)
def _load_dictionary() -> tuple[_DictionaryEntry, ...]:
    try:
        with VOCABULARY_DATA_PATH.open("r", encoding="utf-8") as handle:
            raw_entries = json.load(handle)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Vocabulary data file not found: {VOCABULARY_DATA_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Vocabulary data file is invalid JSON: {VOCABULARY_DATA_PATH}") from exc

    if not isinstance(raw_entries, list):
        raise RuntimeError("Vocabulary data file must contain a top-level list of entries.")

    entries: list[_DictionaryEntry] = []
    for index, item in enumerate(raw_entries):
        entries.append(_parse_entry(item, index))
    return tuple(entries)


def _parse_entry(item: Any, index: int) -> _DictionaryEntry:
    if not isinstance(item, dict):
        raise RuntimeError(f"Vocabulary entry #{index} must be an object.")

    word = _optional_string(item.get("word"), "word", index)
    reading = _optional_string(item.get("reading"), "reading", index)
    if word is None and reading is None:
        raise RuntimeError(f"Vocabulary entry #{index} must include at least one of word or reading.")

    meanings = _string_list(item.get("meanings"), "meanings", index)
    part_of_speech = _string_list(item.get("part_of_speech"), "part_of_speech", index)
    is_common = item.get("is_common", False)
    if not isinstance(is_common, bool):
        raise RuntimeError(f"Vocabulary entry #{index} field 'is_common' must be a boolean.")

    normalized_forms = tuple(
        dict.fromkeys(
            form
            for form in (
                _normalize_lookup_text(word) if word else None,
                _normalize_lookup_text(reading) if reading else None,
            )
            if form
        )
    )

    return _DictionaryEntry(
        word=word,
        reading=reading,
        meanings=tuple(dict.fromkeys(meanings)),
        part_of_speech=tuple(dict.fromkeys(part_of_speech)),
        is_common=is_common,
        normalized_word=_normalize_lookup_text(word) if word else None,
        normalized_reading=_normalize_lookup_text(reading) if reading else None,
        normalized_forms=normalized_forms,
    )


def _optional_string(value: Any, field_name: str, index: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RuntimeError(f"Vocabulary entry #{index} field '{field_name}' must be a string or null.")
    return value


def _string_list(value: Any, field_name: str, index: int) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RuntimeError(f"Vocabulary entry #{index} field '{field_name}' must be a list of strings.")
    return value
