from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import fugashi

MASK_PLACEHOLDER = "[MASK]"


class TargetBaseFormNotFoundError(Exception):
    """Raised when the requested base form does not appear in the sentence."""


@dataclass(frozen=True, slots=True)
class WordMaskMatch:
    answer: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class WordMaskResult:
    masked_sentence: str
    matches: list[WordMaskMatch]


@lru_cache(maxsize=1)
def _english_nlp():
    import spacy

    return spacy.load("en_core_web_sm")


@lru_cache(maxsize=1)
def _japanese_tagger() -> fugashi.Tagger:
    return fugashi.Tagger()


def analyze_word_mask(
    language: Literal["en", "ja"],
    sentence: str,
    target_base_form: str,
) -> WordMaskResult:
    if language == "en":
        matches = _find_english_matches(sentence, target_base_form)
    else:
        matches = _find_japanese_matches(sentence, target_base_form)

    if not matches:
        raise TargetBaseFormNotFoundError

    return WordMaskResult(
        masked_sentence=_mask_sentence(sentence, matches),
        matches=matches,
    )


def _find_english_matches(sentence: str, target_base_form: str) -> list[WordMaskMatch]:
    doc = _english_nlp()(sentence)
    matches: list[WordMaskMatch] = []

    for token in doc:
        if token.lemma_ == target_base_form:
            matches.append(
                WordMaskMatch(
                    answer=token.text,
                    start=token.idx,
                    end=token.idx + len(token.text),
                )
            )

    return matches


def _find_japanese_matches(sentence: str, target_base_form: str) -> list[WordMaskMatch]:
    position = 0
    matches: list[WordMaskMatch] = []

    for word in _japanese_tagger()(sentence):
        surface = word.surface
        lemma = getattr(word.feature, "lemma", None)
        start = sentence.find(surface, position)
        if start == -1:
            start = position
        end = start + len(surface)

        if lemma == target_base_form:
            matches.append(
                WordMaskMatch(
                    answer=surface,
                    start=start,
                    end=end,
                )
            )

        position = end

    return matches


def _mask_sentence(sentence: str, matches: list[WordMaskMatch]) -> str:
    masked_sentence = sentence

    for match in sorted(matches, key=lambda item: item.start, reverse=True):
        masked_sentence = (
            masked_sentence[: match.start]
            + MASK_PLACEHOLDER
            + masked_sentence[match.end :]
        )

    return masked_sentence
