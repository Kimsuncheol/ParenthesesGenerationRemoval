import json
import re
from concurrent.futures import ThreadPoolExecutor

import openai

from app.core.config import settings

_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

# Maps shot type tags (from GPT-4o) to DALL-E compositional modifiers.
_SHOT_MODIFIERS: dict[str, str] = {
    "WIDE": (
        "aerial perspective, full environment visible, characters small in frame, "
        "environmental storytelling, background detail"
    ),
    "MEDIUM": (
        "character dominant, waist-up framing, expressive pose, "
        "mid-range detail, action lines"
    ),
    "CLOSE-UP": (
        "face filling frame, dramatic eyes, emotion-driven, hatching detail, "
        "intimate framing"
    ),
    "EXTREME CLOSE-UP": (
        "single feature fills frame, ink texture prominent, maximum tension, "
        "hyper-detailed hatching"
    ),
    "BIRD'S EYE": (
        "top-down view, figures foreshortened, ground plane visible, "
        "spatial relationship emphasis"
    ),
    "WORM'S EYE": (
        "low angle, figure looming large, sky or ceiling visible, imposing perspective"
    ),
}

_NARRATIVE_STRUCTURE = """\
NARRATIVE STRUCTURE ({panel_count} panels):
{panel_beats}

PANEL TRANSITIONS:
- Between panels 1→2: scene-to-scene (time or space jump)
- Between panels 2→3: action-to-action (same subject, different action)
- Between panels 3→4: moment-to-moment (same action, slight time advance)
- Between panels 4→5: subject-to-subject (different subject, same scene)

RULES:
- Prefix each description with its shot type in brackets, e.g. [WIDE], [MEDIUM], [CLOSE-UP], [EXTREME CLOSE-UP], [BIRD'S EYE], or [WORM'S EYE]
- No two consecutive panels may share the same shot type
- Each description is 15-25 words, visual and present-tense
- Include: character action + environment detail + lighting/atmosphere
- Panels 1 and 4 get the most descriptive detail (largest panels on the page)
- Panel 3 gets the least detail (smallest panel, pure emotion beat)"""

_PANEL_BEATS_5 = """\
  Panel 1 [WIDE]          — Establishing: environment, time of day, spatial context
  Panel 2 [MEDIUM]        — Trigger: the inciting action or conflict begins
  Panel 3 [CLOSE-UP]      — Reaction: character emotion responding to panel 2
  Panel 4 [MEDIUM]        — Escalation: tension peaks or action resolves dramatically
  Panel 5 [WIDE/MEDIUM]   — Resolution: aftermath, emotional landing, or cliffhanger"""

_PANEL_BEATS_GENERIC = """\
  Distribute panels as: establishing → trigger → escalation(s) → resolution.
  Use a mix of [WIDE], [MEDIUM], and [CLOSE-UP] shots across panels."""


def _build_system_prompt(panel_count: int, character_description: str | None) -> str:
    if panel_count == 5:
        beats = _PANEL_BEATS_5
    else:
        beats = _PANEL_BEATS_GENERIC

    structure = _NARRATIVE_STRUCTURE.format(
        panel_count=panel_count,
        panel_beats=beats,
    )

    character_block = ""
    if character_description:
        character_block = f"\nCHARACTER: {character_description}\n"

    return (
        "You are a professional manga storyboard artist designing a single manga page.\n\n"
        + structure
        + character_block
        + f"\n\nOutput a JSON object: {{\"panels\": [/* exactly {panel_count} strings */]}}\n"
        "No text outside the JSON."
    )


def _parse_shot_type(description: str) -> tuple[str, str]:
    """Extract the [SHOT TYPE] tag from the description. Returns (shot_type, clean_description)."""
    match = re.match(r"^\[([A-Z'S ]+)\]\s*", description)
    if match:
        tag = match.group(1).strip()
        clean = description[match.end():]
        return tag, clean
    return "MEDIUM", description


def decompose_prompt(
    prompt: str,
    panel_count: int,
    character_description: str | None = None,
) -> list[str]:
    system_prompt = _build_system_prompt(panel_count, character_description)
    response = _client.chat.completions.create(
        model=settings.MANGA_GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Scene: {prompt}\nPanels: {panel_count}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    data = json.loads(response.choices[0].message.content)
    descriptions = data["panels"]
    if len(descriptions) != panel_count:
        raise ValueError(f"GPT-4o returned {len(descriptions)} panels, expected {panel_count}")
    return descriptions


def _generate_panel_image(description: str, character_description: str | None) -> str:
    shot_type, clean_description = _parse_shot_type(description)
    shot_modifiers = _SHOT_MODIFIERS.get(shot_type, _SHOT_MODIFIERS["MEDIUM"])

    character_block = ""
    if character_description:
        character_block = f"Character: {character_description}. "

    dalle_prompt = (
        f"{settings.MANGA_STYLE_PREFIX}, "
        f"{shot_modifiers}, "
        f"{character_block}"
        f"{clean_description}"
    )

    response = _client.images.generate(
        model=settings.MANGA_DALLE_MODEL,
        prompt=dalle_prompt,
        size="1024x1024",
        quality="standard",
        n=1,
        response_format="url",
    )
    return response.data[0].url


def generate_manga_panels(
    prompt: str,
    panel_count: int,
    character_description: str | None = None,
) -> tuple[list[str], list[str]]:
    descriptions = decompose_prompt(prompt, panel_count, character_description)
    with ThreadPoolExecutor(max_workers=panel_count) as executor:
        futures = [
            executor.submit(_generate_panel_image, desc, character_description)
            for desc in descriptions
        ]
        image_urls = [f.result() for f in futures]
    return descriptions, image_urls
