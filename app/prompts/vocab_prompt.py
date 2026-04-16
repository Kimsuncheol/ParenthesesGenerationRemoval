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

2. Grouping (important)
   - After extracting the target word for every pair, group pairs that share the same dictionary-form word into a single output row.
   - "Same word" means the dictionary form is identical (e.g. 消す groups with 消す).
   - A grouped row represents one spreadsheet row with multiple examples.
   - Preserve the relative order of groups by the first occurrence of each word in the input.

3. "word"
   - Must be the dictionary form of the extracted Japanese vocabulary item.
   - Normalize conjugated forms back to dictionary form.
   - Preserve fixed expressions as full expressions.
   - Examples of fixed expressions include:
     - 気に入る
     - 気にする
     - 気になる
     - 気を付ける
     - 首になる
   - For a grouped row, this is the single shared dictionary form.

4. "meaning_english"
   - Give a short natural English dictionary meaning for the extracted word.
   - Choose the meaning that best matches each sentence's usage.
   - If the row is grouped (multiple examples), format as a numbered list:
     "1. meaning_a\n2. meaning_b"
   - If the row has only one example, write the meaning as a plain string with no number prefix.

5. "meaning_korean"
   - Copy the intended Korean meaning if it correctly matches the extracted word.
   - If the provided Korean meaning is slightly unnatural, normalize it.
   - If grouped, format as a numbered list: "1. 의미_a\n2. 의미_b"
   - If not grouped, write as a plain string.

6. "pronunciation"
   - Must be the full hiragana reading of the extracted word only.
   - No romaji. No spaces.
   - For a grouped row, this is the single shared pronunciation.

7. "example"
   - Copy each input Japanese sentence exactly unless clearly broken.
   - If grouped, format as a numbered list: "1. sentence_a\n2. sentence_b"
   - If not grouped, write as a plain string.

8. "translation_english"
   - Provide a natural English translation of each example sentence.
   - If grouped, format as a numbered list: "1. translation_a\n2. translation_b"
   - If not grouped, write as a plain string.

9. "translation_korean"
   - Provide a natural Korean translation of each example sentence.
   - If grouped, format as a numbered list: "1. 번역_a\n2. 번역_b"
   - If not grouped, write as a plain string.

10. "example_hiragana"
    - Convert each example sentence fully into hiragana. Keep punctuation.
    - If grouped, format as a numbered list: "1. ひらがな_a\n2. ひらがな_b"
    - If not grouped, write as a plain string.

11. Quality rules
    - Do not omit fields.
    - Do not return null.
    - Do not add extra fields.
    - Use natural Japanese, Korean, and English.
    - The extracted word must actually appear in the sentence either directly or as a conjugated form.
    - The extracted word must match the provided Korean meaning as used in the sentence.
    - Numbered list items must use the format "N. value" separated by newlines ("\\n").
    - Do not use bullet points, dashes, or any other list marker.

12. Output count
    - The output array may have fewer items than the input pairs array when grouping occurs.
    - One output row per unique target word, not one row per input pair.

13. Strict output rule
    - Return only the JSON object with a single key "results" whose value is the array.
"""


def build_user_prompt(pairs: list[dict]) -> str:
    """
    Build the user-turn prompt for the vocab extraction task.

    pairs: list of {"example": str, "meaning_korean": str}
    Returns a string that instructs the model to return {"results": [...]}
    with one item per unique target word (may be fewer than len(pairs) when
    multiple pairs share the same word and are grouped into one row).
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
        f"of objects — one per unique target word (pairs sharing the same word are merged "
        f"into one row with numbered lists).\n\n"
        f"Each object must follow this exact schema:\n{schema}\n\n"
        f"{_RULES}"
    )
