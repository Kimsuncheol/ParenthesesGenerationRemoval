import time
from types import SimpleNamespace
from typing import Any

import pytest

from app.services import manga_service


def _make_chat_response(panels: list[str]) -> Any:
    import json

    content = json.dumps({"panels": panels})
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _make_image_response(url: str) -> Any:
    return SimpleNamespace(data=[SimpleNamespace(url=url)])


# --- decompose_prompt ---

def test_decompose_prompt_returns_correct_panel_count(monkeypatch: pytest.MonkeyPatch) -> None:
    panels = [
        "[WIDE] A samurai approaches the village gate at dusk, mist rising from the fields.",
        "[MEDIUM] The samurai draws his katana as an enemy steps from the shadows.",
        "[CLOSE-UP] His eyes narrow sharply, jaw set, reflecting firelight.",
        "[MEDIUM] He lunges forward with a powerful diagonal slash.",
        "[WIDE] The enemy falls; the samurai stands alone in heavy rain.",
    ]

    monkeypatch.setattr(
        manga_service._client.chat.completions,
        "create",
        lambda **kwargs: _make_chat_response(panels),
    )

    result = manga_service.decompose_prompt("A samurai faces an enemy", 5)

    assert result == panels


def test_decompose_prompt_raises_on_wrong_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        manga_service._client.chat.completions,
        "create",
        lambda **kwargs: _make_chat_response(["[WIDE] Only one panel."]),
    )

    with pytest.raises(ValueError, match="expected 3"):
        manga_service.decompose_prompt("A scene", 3)


def test_decompose_prompt_includes_character_in_system_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def mock_create(**kwargs: Any) -> Any:
        captured["messages"] = kwargs["messages"]
        return _make_chat_response(["[WIDE] Panel one.", "[MEDIUM] Panel two."])

    monkeypatch.setattr(manga_service._client.chat.completions, "create", mock_create)

    manga_service.decompose_prompt("A scene", 2, character_description="tall samurai, black hair")

    system_content = captured["messages"][0]["content"]
    assert "tall samurai, black hair" in system_content


def test_decompose_prompt_uses_5panel_narrative_structure(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def mock_create(**kwargs: Any) -> Any:
        captured["messages"] = kwargs["messages"]
        panels = [f"[WIDE] Panel {i}." for i in range(5)]
        return _make_chat_response(panels)

    monkeypatch.setattr(manga_service._client.chat.completions, "create", mock_create)

    manga_service.decompose_prompt("A scene", 5)

    system_content = captured["messages"][0]["content"]
    assert "Establishing" in system_content
    assert "Trigger" in system_content
    assert "Reaction" in system_content
    assert "Escalation" in system_content
    assert "Resolution" in system_content


# --- _parse_shot_type ---

def test_parse_shot_type_extracts_known_tags() -> None:
    cases = [
        ("[WIDE] A village at dusk.", "WIDE", "A village at dusk."),
        ("[MEDIUM] A samurai draws his sword.", "MEDIUM", "A samurai draws his sword."),
        ("[CLOSE-UP] His eyes narrow.", "CLOSE-UP", "His eyes narrow."),
        ("[EXTREME CLOSE-UP] A single tear falls.", "EXTREME CLOSE-UP", "A single tear falls."),
        ("[BIRD'S EYE] Rooftops stretch below.", "BIRD'S EYE", "Rooftops stretch below."),
        ("[WORM'S EYE] The samurai towers overhead.", "WORM'S EYE", "The samurai towers overhead."),
    ]
    for raw, expected_shot, expected_clean in cases:
        shot, clean = manga_service._parse_shot_type(raw)
        assert shot == expected_shot
        assert clean == expected_clean


def test_parse_shot_type_defaults_to_medium_when_no_tag() -> None:
    shot, clean = manga_service._parse_shot_type("No tag here at all.")
    assert shot == "MEDIUM"
    assert clean == "No tag here at all."


# --- _generate_panel_image ---

def test_generate_panel_image_injects_shot_modifiers(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def mock_generate(**kwargs: Any) -> Any:
        captured["prompt"] = kwargs["prompt"]
        return _make_image_response("https://example.com/img.png")

    monkeypatch.setattr(manga_service._client.images, "generate", mock_generate)

    manga_service._generate_panel_image("[WIDE] A village at dusk, rice fields glowing gold.", None)

    assert "aerial perspective" in captured["prompt"]
    assert "environmental storytelling" in captured["prompt"]
    assert "A village at dusk" in captured["prompt"]


def test_generate_panel_image_includes_character_description(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def mock_generate(**kwargs: Any) -> Any:
        captured["prompt"] = kwargs["prompt"]
        return _make_image_response("https://example.com/img.png")

    monkeypatch.setattr(manga_service._client.images, "generate", mock_generate)

    manga_service._generate_panel_image(
        "[MEDIUM] A samurai draws his blade.",
        "tall samurai, black hair, traditional kimono",
    )

    assert "tall samurai, black hair, traditional kimono" in captured["prompt"]


def test_generate_panel_image_includes_style_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def mock_generate(**kwargs: Any) -> Any:
        captured["prompt"] = kwargs["prompt"]
        return _make_image_response("https://example.com/img.png")

    monkeypatch.setattr(manga_service._client.images, "generate", mock_generate)

    manga_service._generate_panel_image("[CLOSE-UP] His eyes narrow.", None)

    from app.core.config import settings
    assert settings.MANGA_STYLE_PREFIX.split(",")[0] in captured["prompt"]


# --- generate_manga_panels ---

def test_generate_manga_panels_returns_ordered_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    descriptions = [
        "[WIDE] Panel 1 desc.",
        "[MEDIUM] Panel 2 desc.",
        "[CLOSE-UP] Panel 3 desc.",
    ]
    delays = [0.05, 0.01, 0.03]

    monkeypatch.setattr(
        manga_service._client.chat.completions,
        "create",
        lambda **kwargs: _make_chat_response(descriptions),
    )

    def mock_generate(**kwargs: Any) -> Any:
        prompt: str = kwargs["prompt"]
        idx = next(i for i, d in enumerate(descriptions) if d.split("] ", 1)[-1] in prompt)
        time.sleep(delays[idx])
        return _make_image_response(f"https://example.com/img_{idx}.png")

    monkeypatch.setattr(manga_service._client.images, "generate", mock_generate)

    returned_descriptions, image_urls = manga_service.generate_manga_panels("A scene", 3)

    assert returned_descriptions == descriptions
    assert image_urls == [
        "https://example.com/img_0.png",
        "https://example.com/img_1.png",
        "https://example.com/img_2.png",
    ]


def test_generate_manga_panels_propagates_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        manga_service._client.chat.completions,
        "create",
        lambda **kwargs: _make_chat_response(["[WIDE] Panel one.", "[MEDIUM] Panel two."]),
    )

    def mock_generate_fail(**kwargs: Any) -> Any:
        raise RuntimeError("upstream image API error")

    monkeypatch.setattr(manga_service._client.images, "generate", mock_generate_fail)

    with pytest.raises(RuntimeError, match="upstream image API error"):
        manga_service.generate_manga_panels("A scene", 2)


def test_generate_manga_panels_passes_character_description(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_prompts: list[str] = []

    monkeypatch.setattr(
        manga_service._client.chat.completions,
        "create",
        lambda **kwargs: _make_chat_response(["[WIDE] Panel one.", "[MEDIUM] Panel two."]),
    )

    def mock_generate(**kwargs: Any) -> Any:
        captured_prompts.append(kwargs["prompt"])
        return _make_image_response("https://example.com/img.png")

    monkeypatch.setattr(manga_service._client.images, "generate", mock_generate)

    manga_service.generate_manga_panels("A scene", 2, character_description="tall samurai")

    assert all("tall samurai" in p for p in captured_prompts)
