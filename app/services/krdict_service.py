"""Korean Learners' Dictionary (krdict) integration for vocabulary enrichment.

Provides a best-effort enrichment step that looks up Korean meanings in the
official Korean Learners' Dictionary (krdict.korean.go.kr) to cross-validate
and enrich vocabulary entries produced by the OpenAI extraction pipeline.

If the krdict API key is not configured, the API is unreachable, or no results
are found, the enrichment step is silently skipped — ensuring the pipeline
never regresses compared to its OpenAI-only behaviour.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import krdict as krdict_lib

from app.core.config import settings
from app.models.schemas import VocabEntry, VocabPair

logger = logging.getLogger(__name__)

_initialised = False


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_krdict() -> None:
    """Set the krdict API key once at application startup.

    Safe to call even when KRDICT_API_KEY is empty — in that case every
    lookup will return ``None`` (graceful degradation).
    """
    global _initialised  # noqa: PLW0603
    if settings.KRDICT_API_KEY:
        krdict_lib.set_key(settings.KRDICT_API_KEY)
        _initialised = True
        logger.info("krdict API key configured — enrichment enabled.")
    else:
        logger.warning(
            "KRDICT_API_KEY is not set. "
            "Vocabulary enrichment via krdict will be skipped."
        )


# ---------------------------------------------------------------------------
# Dataclass for a single lookup result
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class KrdictLookupResult:
    """Relevant fields extracted from a krdict search response."""

    word: str
    """Korean headword (e.g. '지우다')."""

    definition: str
    """Korean-language definition from the dictionary."""

    japanese_translation: str | None
    """Japanese translation string, if available in the response."""


# ---------------------------------------------------------------------------
# Low-level lookup
# ---------------------------------------------------------------------------

def _search_korean(meaning_korean: str) -> KrdictLookupResult | None:
    """Search krdict for a Korean word and return structured data.

    Returns ``None`` on any error or if no results are found.
    """
    if not _initialised:
        return None

    try:
        response = krdict_lib.search(
            query=meaning_korean,
            raise_api_errors=True,
            translation_language=krdict_lib.TranslationLanguage.JAPANESE,
        )
    except Exception:
        logger.warning(
            "krdict search failed for query=%r", meaning_korean, exc_info=True,
        )
        return None

    return _parse_first_result(response)


def _parse_first_result(response: Any) -> KrdictLookupResult | None:
    """Extract the first usable result from a krdict search response."""
    try:
        data = response.data if hasattr(response, "data") else response.get("data")
        if data is None:
            return None

        results = data.results if hasattr(data, "results") else data.get("results")
        if not results:
            return None

        first = results[0]

        word = first.word if hasattr(first, "word") else first.get("word")
        if not word:
            return None

        # --- Korean definition ---
        definition = _extract_definition(first)

        # --- Japanese translation ---
        japanese_translation = _extract_japanese_translation(first)

        return KrdictLookupResult(
            word=word,
            definition=definition or "",
            japanese_translation=japanese_translation,
        )

    except Exception:
        logger.warning("Failed to parse krdict response", exc_info=True)
        return None


def _extract_definition(result: Any) -> str | None:
    """Pull the first Korean definition string from a result object."""
    try:
        # Object-style access (krdict.py typed response)
        if hasattr(result, "definitions"):
            defs = result.definitions
        else:
            defs = result.get("definitions", [])

        if defs:
            first_def = defs[0]
            return (
                first_def.definition
                if hasattr(first_def, "definition")
                else first_def.get("definition")
            )
    except Exception:
        pass
    return None


def _extract_japanese_translation(result: Any) -> str | None:
    """Pull the Japanese translation from a result's first definition."""
    try:
        # Navigate: result -> definitions[0] -> translations
        if hasattr(result, "definitions"):
            defs = result.definitions
        else:
            defs = result.get("definitions", [])

        if not defs:
            return None

        first_def = defs[0]

        translations = (
            first_def.translations
            if hasattr(first_def, "translations")
            else first_def.get("translations", [])
        )

        if not translations:
            return None

        first_trans = translations[0]
        return (
            first_trans.word
            if hasattr(first_trans, "word")
            else first_trans.get("word")
        )
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# High-level enrichment
# ---------------------------------------------------------------------------

def enrich_entries(
    entries: list[VocabEntry],
    pairs: list[VocabPair],
) -> list[VocabEntry]:
    """Enrich extracted vocabulary entries with krdict data.

    For each entry whose corresponding pair(s) contain ``meaning_korean``,
    this function queries krdict to:

    1. Retrieve the authoritative Korean definition.
    2. Retrieve the Japanese translation (if available) for cross-validation
       against the OpenAI-extracted ``word``.

    The function never raises — all errors are logged and the original
    entries are returned unmodified when enrichment fails.

    Parameters
    ----------
    entries:
        Vocabulary entries produced by the OpenAI extraction pipeline.
    pairs:
        The original input pairs (needed to access ``meaning_korean``).

    Returns
    -------
    list[VocabEntry]
        The same entries list, potentially with updated ``meaning_korean``
        fields.
    """
    if not _initialised:
        return entries

    for entry in entries:
        _enrich_single_entry(entry, pairs)

    return entries


def _enrich_single_entry(entry: VocabEntry, pairs: list[VocabPair]) -> None:
    """Try to enrich a single VocabEntry with krdict data."""
    # Collect all non-null meaning_korean values from the original pairs.
    # For grouped entries the meaning_korean may be a numbered list like
    # "1. 지우다\n2. 끄다" — we query each value independently.
    korean_meanings = _collect_korean_meanings(entry, pairs)

    if not korean_meanings:
        return

    for meaning in korean_meanings:
        result = _search_korean(meaning)
        if result is None:
            continue

        # Log cross-validation info
        if result.japanese_translation:
            logger.info(
                "krdict cross-validation: meaning_korean=%r → "
                "krdict_word=%r, japanese_translation=%r, extracted_word=%r",
                meaning,
                result.word,
                result.japanese_translation,
                entry.word,
            )

        # Enrich: if krdict provides a richer definition, append it to
        # the existing meaning_korean (separated by " / ") so both the
        # user-provided meaning and the dictionary definition are preserved.
        if result.definition and result.definition != meaning:
            # Avoid appending if the definition is already present
            if result.definition not in entry.meaning_korean:
                entry.meaning_korean = (
                    f"{entry.meaning_korean} / {result.definition}"
                )

        # Break after the first successful enrichment for this entry
        break


def _collect_korean_meanings(
    entry: VocabEntry,
    pairs: list[VocabPair],
) -> list[str]:
    """Extract individual Korean meaning strings for lookup.

    Handles both single meanings and numbered-list formats like
    ``"1. 지우다\\n2. 끄다"``.
    """
    raw = entry.meaning_korean
    if not raw:
        return []

    lines = raw.strip().split("\n")
    meanings: list[str] = []
    for line in lines:
        cleaned = line.strip()
        # Strip numbered-list prefix ("1. ", "2. ", etc.)
        if len(cleaned) > 3 and cleaned[0].isdigit() and cleaned[1] == ".":
            cleaned = cleaned[3:].strip()
        elif len(cleaned) > 4 and cleaned[:2].isdigit() and cleaned[2] == ".":
            cleaned = cleaned[4:].strip()
        if cleaned:
            meanings.append(cleaned)

    return meanings
