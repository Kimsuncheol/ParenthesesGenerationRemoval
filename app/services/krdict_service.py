"""Korean Learners' Dictionary (krdict) integration for vocabulary extraction.

Primary word extraction engine: looks up Korean meanings in krdict to obtain
Japanese translations, then uses fugashi (MeCab) to match those translations
against lemmas in the example sentence.

Falls back gracefully when the API key is not configured, the API is
unreachable, or no match is found — in those cases ``None`` is returned
and the caller should fall back to OpenAI extraction.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import fugashi
import jaconv
import krdict as krdict_lib

from app.core.config import settings

logger = logging.getLogger(__name__)

_initialised = False
_tagger: fugashi.Tagger | None = None

# Regex to strip particles and other noise from krdict translation strings.
# e.g. "消す（けす）" → "消す",  "消す・けす" → "消す"
_JA_NOISE_RE = re.compile(r"[（(][^)）]*[)）]|[・、。].*$")

# Characters that indicate the translation contains multiple options separated
# by delimiters — e.g. "切る, 消す" or "切る・消す"
_MULTI_WORD_DELIMITERS = re.compile(r"[,，、・/／]")


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_krdict() -> None:
    """Set the krdict API key and initialise fugashi tagger at startup.

    Safe to call even when KRDICT_API_KEY is empty — in that case every
    extraction will return ``None`` (graceful degradation).
    """
    global _initialised, _tagger  # noqa: PLW0603
    if settings.KRDICT_API_KEY:
        krdict_lib.set_key(settings.KRDICT_API_KEY)
        _tagger = fugashi.Tagger()
        _initialised = True
        logger.info("krdict API key configured — krdict extraction enabled.")
    else:
        logger.warning(
            "KRDICT_API_KEY is not set. "
            "krdict word extraction will be skipped (OpenAI fallback)."
        )


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class KrdictExtraction:
    """Result of a successful krdict-based word extraction."""

    word: str
    """Dictionary-form Japanese word extracted from the sentence (e.g. '消す')."""

    pronunciation: str
    """Hiragana reading of the word (e.g. 'けす')."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_word_from_sentence(
    sentence: str,
    meaning_korean: str,
) -> KrdictExtraction | None:
    """Try to extract the target Japanese word from *sentence* using *meaning_korean*.

    Steps:
      1. Look up *meaning_korean* in krdict → obtain Japanese translation(s).
      2. Tokenise *sentence* with fugashi (MeCab) → get lemma for each token.
      3. Match any krdict Japanese translation against the token lemmas.
      4. Return ``KrdictExtraction`` on success, or ``None`` to signal fallback.

    This function never raises — all errors are logged and ``None`` returned.
    """
    if not _initialised or _tagger is None:
        return None

    # Step 1: krdict lookup
    japanese_candidates = _lookup_japanese_translations(meaning_korean)
    if not japanese_candidates:
        logger.debug(
            "krdict: no Japanese translations for meaning_korean=%r",
            meaning_korean,
        )
        return None

    # Step 2: tokenise the sentence
    try:
        tokens = _tagger(sentence)
    except Exception:
        logger.warning("fugashi tokenisation failed for sentence=%r", sentence, exc_info=True)
        return None

    # Step 3 & 4: match
    return _match_candidates_in_tokens(japanese_candidates, tokens)


# ---------------------------------------------------------------------------
# krdict lookup helpers
# ---------------------------------------------------------------------------

def _lookup_japanese_translations(meaning_korean: str) -> list[str]:
    """Query krdict for *meaning_korean* and return cleaned Japanese words."""
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
        return []

    return _parse_japanese_translations(response)


def _parse_japanese_translations(response: Any) -> list[str]:
    """Extract all unique Japanese translation strings from a krdict response."""
    candidates: list[str] = []

    try:
        data = response.data if hasattr(response, "data") else response.get("data")
        if data is None:
            return []

        results = data.results if hasattr(data, "results") else data.get("results")
        if not results:
            return []

        for result in results:
            _collect_translations_from_result(result, candidates)

    except Exception:
        logger.warning("Failed to parse krdict response", exc_info=True)

    return candidates


def _collect_translations_from_result(result: Any, candidates: list[str]) -> None:
    """Append Japanese translation words from a single krdict result."""
    try:
        if hasattr(result, "definitions"):
            defs = result.definitions
        else:
            defs = result.get("definitions", [])

        for defn in defs:
            translations = (
                defn.translations
                if hasattr(defn, "translations")
                else defn.get("translations", [])
            )
            for trans in translations:
                raw_word = (
                    trans.word
                    if hasattr(trans, "word")
                    else trans.get("word")
                )
                if not raw_word or not isinstance(raw_word, str):
                    continue

                for cleaned in _clean_japanese_translation(raw_word):
                    if cleaned and cleaned not in candidates:
                        candidates.append(cleaned)
    except Exception:
        pass


def _clean_japanese_translation(raw: str) -> list[str]:
    """Clean a raw krdict Japanese translation string into candidate words.

    Handles cases like:
      - "消す（けす）" → ["消す"]
      - "切る、消す" → ["切る", "消す"]
      - "消す" → ["消す"]
    """
    # First strip parenthetical readings
    cleaned = _JA_NOISE_RE.sub("", raw).strip()

    if not cleaned:
        return []

    # Split on delimiters if present (e.g. "切る、消す")
    if _MULTI_WORD_DELIMITERS.search(cleaned):
        parts = _MULTI_WORD_DELIMITERS.split(cleaned)
        return [p.strip() for p in parts if p.strip()]

    return [cleaned]


# ---------------------------------------------------------------------------
# Fugashi-based sentence matching
# ---------------------------------------------------------------------------

def _match_candidates_in_tokens(
    candidates: list[str],
    tokens: list,
) -> KrdictExtraction | None:
    """Try to match any candidate Japanese word against token lemmas.

    Handles both single-token words (e.g. 消す) and multi-token idiomatic
    expressions (e.g. 気に入る).
    """
    # Build token data for efficient matching
    token_data = []
    for t in tokens:
        feat = t.feature
        lemma = getattr(feat, "lemma", None)
        orthBase = getattr(feat, "orthBase", None)
        kanaBase = getattr(feat, "kanaBase", None)
        surface = t.surface

        # Clean lemma — fugashi sometimes appends tags like "バス-bus"
        if lemma and "-" in lemma:
            lemma = lemma.split("-")[0]

        token_data.append({
            "surface": surface,
            "lemma": lemma,
            "orthBase": orthBase,
            "kanaBase": kanaBase,
        })

    for candidate in candidates:
        result = _try_match_candidate(candidate, token_data)
        if result is not None:
            return result

    return None


def _try_match_candidate(
    candidate: str,
    token_data: list[dict],
) -> KrdictExtraction | None:
    """Try to match a single candidate word against the token list."""
    # Strategy 1: single-token match (most common case)
    for td in token_data:
        if td["lemma"] == candidate or td["orthBase"] == candidate:
            kana = td["kanaBase"]
            if not kana:
                continue
            pronunciation = jaconv.kata2hira(kana)
            # Use orthBase as the word (dictionary form) if available
            word = td["orthBase"] or td["lemma"] or candidate
            return KrdictExtraction(word=word, pronunciation=pronunciation)

    # Strategy 2: multi-token match for compound expressions
    # e.g. candidate="気に入る" → tokens ["気", "に", "入る"]
    if len(candidate) > 1:
        result = _try_multi_token_match(candidate, token_data)
        if result is not None:
            return result

    return None


def _try_multi_token_match(
    candidate: str,
    token_data: list[dict],
) -> KrdictExtraction | None:
    """Match a compound expression by concatenating consecutive token surfaces/orthBases."""
    n = len(token_data)

    for start in range(n):
        # Try concatenating tokens from this starting position
        concat_surface = ""
        concat_orthBase = ""
        concat_kana = ""

        for end in range(start, min(start + 6, n)):  # limit to 6 tokens
            concat_surface += token_data[end]["surface"]
            concat_orthBase += (token_data[end]["orthBase"] or token_data[end]["surface"])
            concat_kana += (token_data[end]["kanaBase"] or "")

            # Check if the concatenated orthBase matches the candidate
            if concat_orthBase == candidate:
                if concat_kana:
                    pronunciation = jaconv.kata2hira(concat_kana)
                    return KrdictExtraction(
                        word=candidate,
                        pronunciation=pronunciation,
                    )

    return None
