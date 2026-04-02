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


def test_decompose_prompt_returns_correct_panel_count(monkeypatch: pytest.MonkeyPatch) -> None:
    panels = ["Panel one.", "Panel two.", "Panel three."]

    monkeypatch.setattr(
        manga_service._client.chat.completions,
        "create",
        lambda **kwargs: _make_chat_response(panels),
    )

    result = manga_service.decompose_prompt("A samurai walks through a village", 3)

    assert result == panels


def test_decompose_prompt_raises_on_wrong_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        manga_service._client.chat.completions,
        "create",
        lambda **kwargs: _make_chat_response(["Only one panel."]),
    )

    with pytest.raises(ValueError, match="expected 3"):
        manga_service.decompose_prompt("A scene", 3)


def test_generate_manga_panels_returns_ordered_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    descriptions = ["Panel 1 desc.", "Panel 2 desc.", "Panel 3 desc."]
    delays = [0.05, 0.01, 0.03]

    monkeypatch.setattr(
        manga_service._client.chat.completions,
        "create",
        lambda **kwargs: _make_chat_response(descriptions),
    )

    call_order: list[str] = []

    def mock_generate(**kwargs: Any) -> Any:
        prompt: str = kwargs["prompt"]
        idx = next(i for i, d in enumerate(descriptions) if d in prompt)
        time.sleep(delays[idx])
        call_order.append(descriptions[idx])
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
        lambda **kwargs: _make_chat_response(["Panel one.", "Panel two."]),
    )

    def mock_generate_fail(**kwargs: Any) -> Any:
        raise RuntimeError("upstream image API error")

    monkeypatch.setattr(manga_service._client.images, "generate", mock_generate_fail)

    with pytest.raises(RuntimeError, match="upstream image API error"):
        manga_service.generate_manga_panels("A scene", 2)
