import json

SYSTEM_PROMPT: str = (
    "You are a Japanese vocabulary extraction assistant for a Korean learner app.\n\n"
    "Your task is to identify the Japanese target expression from each Japanese sentence "
    "based on the provided Korean meaning, then return structured vocabulary data for "
    "spreadsheet insertion.\n\n"
    "IMPORTANT: Some input pairs may already include a pre-extracted \"word\" field. "
    "When a \"word\" is provided, you MUST use it as-is and NOT re-extract from the sentence. "
    "Only fill in the remaining fields (meaning_english, meaning_korean, pronunciation, "
    "translation_english, translation_korean, example_hiragana).\n\n"
    "CRITICAL RULE: The \"word\" field must NEVER contain a standalone Japanese particle "
    "(は, が, を, に, で, へ, と, の, から, まで) as a prefix. "
    "Write only the verb or expression in dictionary form. "
    "WRONG: をしまう, を消す, に乗る. CORRECT: しまう, 消す, 乗る.\n\n"
    "Return only valid JSON.\n"
    "Do not include markdown.\n"
    "Do not include explanations.\n"
    "Do not include any text before or after the JSON."
)

_RULES: str = """\
Rules:
1. Target extraction
   - If a "word" field is already provided in the input pair, use it exactly as-is.
     Do NOT re-extract or change it.
   - Otherwise, identify the Japanese word or fixed expression in the sentence that
     matches the provided Korean meaning.
   - Extract the best matching vocabulary item only.
   - Do not extract unrelated words from the sentence.
   - If multiple expressions are possible, choose the one that most directly matches the Korean meaning.

2. Grouping (important)
   - After extracting the target word for every pair, group pairs that share the same dictionary-form word into a single output row.
   - "Same word" means the dictionary form is identical (e.g. 消す groups with 消す).
   - A grouped row represents one spreadsheet row with multiple examples.
   - Preserve the relative order of groups by the first occurrence of each word in the input.

3. "word"
   - If pre-extracted in the input, use it exactly as provided.
   - Otherwise, must be the dictionary form of the extracted Japanese vocabulary item only.
   - NEVER prefix the word with a standalone particle (は, が, を, に, で, へ, と, の, から, まで).
     WRONG: をしまう / を消す / に乗る / で働く
     CORRECT: しまう / 消す / 乗る / 働く
   - Normalize conjugated forms back to dictionary form (e.g. 消して → 消す, 乗った → 乗る).
   - Do NOT include the sentence's subject, object noun, or any surrounding words.
   - Exception — fixed idiomatic expressions where the particle is inseparable from the
     expression (not a grammatical case particle):
     e.g. 気に入る, 気にする, 気になる, 気を付ける, 首になる.
     These must be written in full as fixed expressions.
   - For a grouped row, this is the single shared value.

4. "meaning_english"
   - Give a short natural English dictionary meaning for the extracted word.
   - Choose the meaning that best matches each sentence's usage.
   - If the row is grouped (multiple examples), format as a numbered list using \\n as the
     line separator: "1. meaning_a\\n2. meaning_b"
   - If the row has only one example, write the meaning as a plain string with no number prefix.

5. "meaning_korean"
   - Generate a short natural Korean dictionary meaning for the extracted word.
   - Choose the meaning that best matches each sentence's usage.
   - If grouped, format as a numbered list: "1. 의미_a\\n2. 의미_b"
   - If not grouped, write as a plain string.

6. "_indices"
   - Must be an array of the 0-based integer indices of the input pairs that were grouped into this row.
   - If only one pair maps to this row, write a single-element array: [2].
   - If multiple pairs were grouped, list all their indices in input order: [0, 1].
   - This field is required on every output object.

7. "pronunciation"
   - If a "pronunciation" field is already provided in the input pair, use it as-is.
   - Otherwise, must be the full hiragana reading of the extracted word only.
   - No romaji. No spaces.
   - For a grouped row, this is the single shared pronunciation.

8. "translation_english"
   - Provide a natural English translation of each example sentence.
   - If grouped, format as a numbered list: "1. translation_a\\n2. translation_b"
   - If not grouped, write as a plain string.

9. "translation_korean"
   - Provide a natural Korean translation of each example sentence.
   - If grouped, format as a numbered list: "1. 번역_a\\n2. 번역_b"
   - If not grouped, write as a plain string.

10. "example_hiragana"
    - Convert each example sentence fully into hiragana. Keep punctuation.
    - If grouped, format as a numbered list: "1. ひらがな_a\\n2. ひらがな_b"
    - If not grouped, write as a plain string.

11. Quality rules
    - Do not omit fields.
    - Do not return null.
    - Do not add extra fields beyond the schema.
    - "_indices" is required on every output object.
    - Use natural Japanese, Korean, and English.
    - The extracted word must actually appear in the sentence either directly or as a conjugated form.
    - The extracted word must match the provided meaning as used in the sentence.
    - Numbered list items must be separated by \\n (a JSON newline escape), not by spaces or commas.
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

    pairs: list of dicts with "example" and whichever of
    "meaning_korean" / "meaning_english" were provided by the caller.
    May also include pre-extracted "word" and "pronunciation" fields from
    krdict — in that case OpenAI should use them as-is.

    Returns a string that instructs the model to return {"results": [...]}
    with one item per unique target word (may be fewer than len(pairs) when
    multiple pairs share the same word and are grouped into one row).
    """
    pairs_json = json.dumps(pairs, ensure_ascii=False, indent=2)
    schema = """{
  "_indices": [0],
  "word": "string",
  "meaning_english": "string",
  "meaning_korean": "string",
  "pronunciation": "string",
  "translation_english": "string",
  "translation_korean": "string",
  "example_hiragana": "string"
}"""
    grouped_example = (
        '{\n'
        '  "_indices": [0, 1],\n'
        '  "word": "消す",\n'
        '  "meaning_english": "1. erase\\n2. turn off",\n'
        '  "meaning_korean": "1. 지우다\\n2. 끄다",\n'
        '  "pronunciation": "けす",\n'
        '  "translation_english": "1. Erase the letters on the blackboard.\\n2. Turn off the TV.",\n'
        '  "translation_korean": "1. 칠판의 글씨를 지우다.\\n2. TV를 끄다.",\n'
        '  "example_hiragana": "1. こくばんのじをけす。\\n2. てれびをけす。"\n'
        '}'
    )
    particle_reminder = (
        "REMINDER — word field: write the verb in plain dictionary form only. "
        "Never prefix it with a particle. "
        "消す NOT を消す. しまう NOT をしまう. 乗る NOT に乗る."
    )

    # Check if any pairs have pre-extracted words
    has_pre_extracted = any("word" in p for p in pairs)
    pre_extract_note = ""
    if has_pre_extracted:
        pre_extract_note = (
            "\n\nNOTE: Some input pairs include a pre-extracted \"word\" and/or "
            "\"pronunciation\" field. For these pairs, use the provided word/pronunciation "
            "as-is and only generate the remaining fields. "
            "Still group pairs that share the same word."
        )

    return (
        f"{particle_reminder}\n\n"
        f"Input pairs:\n{pairs_json}\n\n"
        f"Return a JSON object with a single key \"results\" whose value is an array "
        f"of objects — one per unique target word (pairs sharing the same word are merged "
        f"into one row with numbered lists separated by \\n).\n\n"
        f"Each object must follow this exact schema:\n{schema}\n\n"
        f"Example of a correctly grouped row (two pairs sharing 消す):\n{grouped_example}\n\n"
        f"{_RULES}"
        f"{pre_extract_note}"
    )
