import json
from concurrent.futures import ThreadPoolExecutor

import openai

from app.core.config import settings

_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)


def decompose_prompt(prompt: str, panel_count: int) -> list[str]:
    response = _client.chat.completions.create(
        model=settings.MANGA_GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a manga storyboard artist. "
                    "Given a scene description and a panel count, output exactly that many "
                    "sequential panel descriptions. Each description must be a self-contained, "
                    "visual, present-tense sentence of 10-20 words suitable as a DALL-E image prompt. "
                    "Output a JSON object with a single key 'panels' whose value is an array of "
                    "exactly that many strings. No additional text outside the JSON."
                ),
            },
            {
                "role": "user",
                "content": f"Scene: {prompt}\nPanels: {panel_count}",
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    data = json.loads(response.choices[0].message.content)
    descriptions = data["panels"]
    if len(descriptions) != panel_count:
        raise ValueError(f"GPT-4o returned {len(descriptions)} panels, expected {panel_count}")
    return descriptions


def _generate_panel_image(description: str) -> str:
    response = _client.images.generate(
        model=settings.MANGA_DALLE_MODEL,
        prompt=(
            "Manga panel, black and white ink illustration, detailed line art, dramatic composition: "
            + description
        ),
        size="1024x1024",
        quality="standard",
        n=1,
        response_format="url",
    )
    return response.data[0].url


def generate_manga_panels(prompt: str, panel_count: int) -> tuple[list[str], list[str]]:
    descriptions = decompose_prompt(prompt, panel_count)
    with ThreadPoolExecutor(max_workers=panel_count) as executor:
        futures = [executor.submit(_generate_panel_image, desc) for desc in descriptions]
        image_urls = [f.result() for f in futures]
    return descriptions, image_urls
