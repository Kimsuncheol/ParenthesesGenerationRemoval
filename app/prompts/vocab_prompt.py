import json

SYSTEM_PROMPT: str = (
    "You are a Japanese vocabulary extraction assistant for a Korean learner app.\n\n"
    "Your task is to identify the Japanese target expression from each Japanese sentence "
    "based on the provided Korean meaning, then return structured vocabulary data for "
    "spreadsheet insertion.\n\n"
    "Return only valid JSON.\n"
    "Do not include markdown.\n"
    "Do not include explanations.\n"
    "Do not include any text before or after the JSON."
)

_RULES: str = """\
Rules:
1. Target extraction
   - Identify the Japanese word or fixed expression in the sentence that matches the provided Korean meaning.
   - Extract the best matching vocabulary item only.
   - Do not extract unrelated words from the sentence.
   - If multiple expressions are possible, choose the one that most directly matches the Korean meaning.

2. "word"
   - Must be the dictionary form of the extracted Japanese vocabulary item.
   - Normalize conjugated forms back to dictionary form.
   - Preserve fixed expressions as full expressions.
   - Examples of fixed expressions include:
     - 気に入る
     - 気にする
     - 気になる
     - 気を付ける
     - 首になる

3. "meaning_english"
   - Give a short natural English dictionary meaning for the extracted word.
   - Choose the meaning that best matches the sentence usage.

4. "meaning_korean"
   - Copy the intended Korean meaning if it correctly matches the extracted word.
   - If the provided Korean meaning is slightly unnatural, normalize it into a short natural Korean dictionary meaning while preserving the intended sense.

5. "pronunciation"
   - Must be the full hiragana reading of the extracted word only.
   - No romaji.
   - No spaces.

6. "example"
   - Copy the input Japanese sentence exactly unless it is clearly broken.
   - Keep the sentence natural.

7. "translation_english"
   - Provide a natural English translation of the full example sentence.

8. "translation_korean"
   - Provide a natural Korean translation of the full example sentence.

9. "example_hiragana"
   - Convert the full example sentence into hiragana.
   - Keep punctuation.
   - Replace kanji with hiragana.

10. Quality rules
    - Do not omit fields.
    - Do not return null.
    - Do not add extra fields.
    - Use natural Japanese, Korean, and English.
    - The extracted word must actually appear in the sentence either directly or as a conjugated form.
    - The extracted word must match the provided Korean meaning as used in the sentence.

11. Order
    - Return items in the same order as the input "pairs" array.

12. Strict output rule
    - Return only the JSON object with a single key "results" whose value is the array.
"""


def build_user_prompt(pairs: list[dict]) -> str:
    """
    Build the user-turn prompt for the vocab extraction task.

    pairs: list of {"example": str, "meaning_korean": str}
    Returns a string that instructs the model to return {"results": [...]}
    with exactly len(pairs) items in order.
    """
    pairs_json = json.dumps(pairs, ensure_ascii=False, indent=2)
    schema = """{
  "word": "string",
  "meaning_english": "string",
  "meaning_korean": "string",
  "pronunciation": "string",
  "example": "string",
  "translation_english": "string",
  "translation_korean": "string",
  "example_hiragana": "string"
}"""
    return (
        f"Input pairs:\n{pairs_json}\n\n"
        f"Return a JSON object with a single key \"results\" whose value is an array "
        f"of exactly {len(pairs)} objects, one per input pair, in the same order.\n\n"
        f"Each object must follow this exact schema:\n{schema}\n\n"
        f"{_RULES}"
    )
