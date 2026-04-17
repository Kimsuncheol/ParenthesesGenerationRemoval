import json


SYSTEM_PROMPT = """\
You are a vocabulary quiz generation assistant.

Return only valid JSON. Do not include markdown, explanations, or any text outside the JSON object.
"""


def build_fill_blank_prompt(rows: list[dict]) -> str:
    rows_json = json.dumps(rows, ensure_ascii=False, indent=2)
    schema = """{
  "results": [
    {
      "id": "q1",
      "sentence": "sentence with exactly one _ blank",
      "translation_english": "English translation or null",
      "translation_korean": "Korean translation or null",
      "options": ["correct or distractor", "correct or distractor", "correct or distractor", "correct or distractor"],
      "answer_text": "the exact correct option text"
    }
  ]
}"""
    return f"""\
Create fill-in-the-blank vocabulary quiz questions from these rows.

Input rows:
{rows_json}

Rules:
1. Return one result for every input row, preserving the same id values and order.
2. The sentence must contain exactly one blank marker: _.
3. Replace the target expression, its derivative, inflected form, conjugated form, or related form in the example sentence with _.
4. Do not leave the answer text visible anywhere in the sentence.
5. Return exactly four options per result.
6. Include the correct answer_text exactly once in options.
7. Distractors must match the target language and be plausible for the target's part of speech or grammatical form.
8. For Japanese, options may be dictionary forms, inflected forms, conjugated forms, or related forms when that best fits the blank.
9. For English collocations, options should be collocations of the same grammatical type.
10. Copy or preserve the provided translations when present.

Return this exact JSON shape:
{schema}
"""
