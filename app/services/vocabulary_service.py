import re
from typing import Any

import requests

from app.core.config import settings
from app.models.text_models import VocabularyEntry
from app.services import romanization_service

_MAX_MEANINGS = 5
_JAPANESE_TEXT_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\u31f0-\u31ff々ー]")
_PLACEHOLDER_PARTS_OF_SPEECH = {"Wikipedia definition", "Other forms", "Notes"}


def lookup_vocabulary(text: str) -> VocabularyEntry | None:
    raw_query = text.strip()
    if not raw_query or not _contains_japanese(text):
        return None

    response = requests.get(
        settings.JISHO_API_URL,
        params={"keyword": raw_query},
        timeout=settings.JISHO_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Jisho API returned an invalid payload.")

    data = payload.get("data")
    if not isinstance(data, list):
        raise RuntimeError("Jisho API payload is missing a valid 'data' list.")

    best_entry = _select_best_entry(data, raw_query)
    if best_entry is None:
        return None

    word, reading = _extract_primary_japanese(best_entry)
    romanized = romanization_service.romanize_ja(reading) if reading else None
    return VocabularyEntry(
        word=word,
        reading=reading,
        romanized=romanized,
        meanings=_extract_meanings(best_entry),
        part_of_speech=_extract_part_of_speech(best_entry),
        is_common=bool(best_entry.get("is_common", False)),
    )


def _contains_japanese(text: str) -> bool:
    return bool(_JAPANESE_TEXT_RE.search(text))


def _select_best_entry(entries: list[Any], raw_query: str) -> dict[str, Any] | None:
    valid_entries = [entry for entry in entries if isinstance(entry, dict)]
    if not valid_entries:
        return None

    for entry in valid_entries:
        word, _ = _extract_primary_japanese(entry)
        if word == raw_query:
            return entry

    for entry in valid_entries:
        _, reading = _extract_primary_japanese(entry)
        if reading == raw_query:
            return entry

    return valid_entries[0]


def _extract_primary_japanese(entry: dict[str, Any]) -> tuple[str | None, str | None]:
    japanese = entry.get("japanese")
    if not isinstance(japanese, list) or not japanese:
        return None, None

    first = japanese[0]
    if not isinstance(first, dict):
        return None, None

    word = first.get("word")
    reading = first.get("reading")
    return (
        word if isinstance(word, str) else None,
        reading if isinstance(reading, str) else None,
    )


def _extract_meanings(entry: dict[str, Any]) -> list[str]:
    senses = entry.get("senses")
    if not isinstance(senses, list):
        raise RuntimeError("Jisho API entry is missing a valid 'senses' list.")

    meanings: list[str] = []
    for sense in senses:
        if not isinstance(sense, dict):
            continue
        english_definitions = sense.get("english_definitions")
        if not isinstance(english_definitions, list):
            continue
        for definition in english_definitions:
            if isinstance(definition, str) and definition and definition not in meanings:
                meanings.append(definition)
                if len(meanings) >= _MAX_MEANINGS:
                    return meanings
    return meanings


def _extract_part_of_speech(entry: dict[str, Any]) -> list[str]:
    senses = entry.get("senses")
    if not isinstance(senses, list):
        raise RuntimeError("Jisho API entry is missing a valid 'senses' list.")

    parts_of_speech: list[str] = []
    for sense in senses:
        if not isinstance(sense, dict):
            continue
        raw_parts = sense.get("parts_of_speech")
        if not isinstance(raw_parts, list):
            continue
        for part in raw_parts:
            if (
                isinstance(part, str)
                and part
                and part not in _PLACEHOLDER_PARTS_OF_SPEECH
                and part not in parts_of_speech
            ):
                parts_of_speech.append(part)
    return parts_of_speech
