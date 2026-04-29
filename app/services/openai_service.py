import json
import logging

import openai
from pydantic import ValidationError

from app.core.config import settings
from app.models.schemas import VocabEntry, VocabPair
from app.prompts.vocab_prompt import SYSTEM_PROMPT, build_user_prompt
from app.services import krdict_service

logger = logging.getLogger(__name__)

_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

# Ordered longest-first so "から" and "まで" are tried before their first character.
_LEADING_PARTICLES = ("から", "まで", "は", "が", "を", "に", "で", "へ", "と", "の")


def _strip_leading_particle(word: str) -> str:
    """Remove a leading grammatical particle from a word field if present.

    Fixed expressions such as 気に入る or 気を付ける start with a kanji (気),
    so they are never affected. Only plain particle-prefixed verbs like
    を消す → 消す or に乗る → 乗る are stripped.
    """
    for particle in _LEADING_PARTICLES:
        if word.startswith(particle) and len(word) > len(particle):
            return word[len(particle):]
    return word


def extract_vocab(pairs: list[VocabPair]) -> list[VocabEntry]:
    """
    Extract vocabulary from (example, meaning) pairs using a two-phase pipeline.

    Phase 1 — krdict extraction (per pair):
        For each pair with meaning_korean, try to extract the target word
        via krdict lookup + fugashi sentence tokenisation.

    Phase 2 — OpenAI completion:
        Send all pairs to OpenAI. Pairs with pre-extracted words include
        "word" and "pronunciation" hints so OpenAI only needs to fill in
        the remaining fields (translations, hiragana, etc.).
        Pairs where krdict failed get full OpenAI extraction as before.

    Raises:
        openai.OpenAIError    -- network, auth, rate-limit, or server errors; caller maps to HTTP 502
        ValueError            -- structurally wrong response (missing key, empty array); caller maps to HTTP 502
        pydantic.ValidationError -- field-level validation failure in OpenAI output; caller maps to HTTP 422
    """
    # ── Phase 1: krdict extraction ──────────────────────────────────────
    krdict_results: list[krdict_service.KrdictExtraction | None] = []
    for p in pairs:
        if p.meaning_korean:
            extraction = krdict_service.extract_word_from_sentence(
                sentence=p.example,
                meaning_korean=p.meaning_korean,
            )
            krdict_results.append(extraction)
            if extraction:
                logger.info(
                    "krdict extracted: meaning_korean=%r → word=%r, pronunciation=%r",
                    p.meaning_korean,
                    extraction.word,
                    extraction.pronunciation,
                )
        else:
            krdict_results.append(None)

    krdict_count = sum(1 for r in krdict_results if r is not None)
    logger.info(
        "krdict extraction: %d/%d pairs succeeded",
        krdict_count,
        len(pairs),
    )

    # ── Phase 2: OpenAI for remaining fields ────────────────────────────
    raw_pairs = []
    for i, p in enumerate(pairs):
        d: dict = {"example": p.example}
        if p.meaning_korean:
            d["meaning_korean"] = p.meaning_korean
        if p.meaning_english:
            d["meaning_english"] = p.meaning_english

        # Include pre-extracted word hints from krdict
        extraction = krdict_results[i]
        if extraction is not None:
            d["word"] = extraction.word
            d["pronunciation"] = extraction.pronunciation

        raw_pairs.append(d)

    user_prompt = build_user_prompt(raw_pairs)

    response = _client.chat.completions.create(
        model=settings.VOCAB_GPT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    raw_text = response.choices[0].message.content

    # Stage 1: JSON parse
    data = json.loads(raw_text)

    # Stage 2: structural validation
    if not isinstance(data, dict) or "results" not in data:
        raise ValueError(
            f"OpenAI response missing 'results' key. Got keys: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}"
        )

    raw_results = data["results"]

    if not isinstance(raw_results, list):
        raise ValueError(
            f"OpenAI 'results' field is not a list, got {type(raw_results).__name__}."
        )

    if len(raw_results) == 0:
        raise ValueError("OpenAI returned an empty 'results' array.")

    if len(raw_results) > len(pairs):
        raise ValueError(
            f"OpenAI returned {len(raw_results)} items, which exceeds the {len(pairs)} input pairs."
        )

    all_indices = [i for item in raw_results for i in item.get("_indices", [])]
    out_of_range = [i for i in all_indices if not (0 <= i < len(pairs))]
    if out_of_range:
        raise ValueError(f"OpenAI returned out-of-range _indices: {out_of_range}.")

    # Stage 3: reconstruct example, meaning_korean, and meaning_english from original input.
    # Fields provided by the caller are never modified by OpenAI — we overwrite whatever
    # OpenAI generated with the verbatim request values.
    # Also enforce krdict-extracted word/pronunciation when available.
    for item in raw_results:
        indices: list[int] = sorted(item.pop("_indices", []))
        if not indices:
            raise ValueError("OpenAI response item missing required '_indices' field.")

        example_values = [pairs[i].example for i in indices]
        korean_values  = [pairs[i].meaning_korean for i in indices]
        english_values = [pairs[i].meaning_english for i in indices]

        def _join(values: list) -> str | None:
            non_null = [v for v in values if v is not None]
            if not non_null:
                return None
            if len(non_null) == 1 and len(values) == 1:
                return non_null[0]
            return "\n".join(f"{n}. {v}" for n, v in enumerate(values, start=1) if v is not None)

        item["example"] = (
            example_values[0] if len(indices) == 1
            else "\n".join(f"{n}. {v}" for n, v in enumerate(example_values, start=1))
        )

        korean_str = _join(korean_values)
        if korean_str is not None:
            item["meaning_korean"] = korean_str

        english_str = _join(english_values)
        if english_str is not None:
            item["meaning_english"] = english_str

        # Enforce krdict-extracted word and pronunciation for the first pair in the group.
        # If krdict succeeded for any pair in this group, use its word/pronunciation.
        for idx in indices:
            extraction = krdict_results[idx]
            if extraction is not None:
                item["word"] = extraction.word
                item["pronunciation"] = extraction.pronunciation
                break

    # Stage 4: per-item Pydantic validation — raises ValidationError on failure
    entries = [VocabEntry.model_validate(item) for item in raw_results]

    # Stage 5: strip any leading grammatical particle the model prepended to word
    for entry in entries:
        entry.word = _strip_leading_particle(entry.word)

    return entries
