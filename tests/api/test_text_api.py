import sys
from pathlib import Path
from typing import Any

import pytest
import requests
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from main import app
from app.services import vocabulary_service

client = TestClient(app)


PLACEHOLDER_ONLY_INPUT = """スイッチを入()れる。
黒()いスーツを着()る。
スーツケースを持()ち歩()く。
スーパーに買()い物()に行()く。
映()画()をスクリーン位()映()す。
ステーキを焼()く。"""

PLACEHOLDER_ONLY_EXPECTED = """スイッチを入(い)れる。
黒(くろ)いスーツを着(き)る。
スーツケースを持(も)ち歩(ある)く。
スーパーに買(か)い物(もの)に行(い)く。
映(えい)画(が)をスクリーン位(くらい)映(うつ)す。
ステーキを焼(や)く。"""

MIXED_INPUT = """オートバイに乗(の)って走(はし)る。
部(へ)屋(や)のカーテンを閉(し)める。
ガスの火(ひ)を強(つよ)くする。
ガソリンの値(ね)段(だん)が上(あ)がる。
近(ちか)くのガソリンスタンドを探(さが)す。
ガラスは壊(こわ)れやすい。
昼(ちゅう)食(しょく)はカレーにする。
キッチンで料(りょう)理(り)をする。
体(たい)重(じゅう)が５キロメートルも増(ふ)えてしまった。
時(じ)速(そく)１００キロメートルで走(はし)る。
ケーキを半(はん)分(ぶん)に切(き)る。
ケースに入(い)れる。
市(し)民(みん)ホールでコンサートが開(ひら)かれた。
を使(つか)ってメールを送(おく)る。
作家(さっか)にサインをもらう。
友(とも)達(だち)とサッカーを見(み)に行(い)く。
野菜(やさい)サラダを食(た)べる。
夏(なつ)はやはりサンダルがいい。
ハムと野菜(やさい)の入(はい)ったサンドイッチを買(か)った。
イチゴジャムを塗(ぬ)って食(た)べる。
オラン時(じ)ジュースを飲(の)む。
スイッチを入(い)れる。
黒(くろ)いスーツを着(き)る。
スーツケースを持(も)ち歩(ある)く。
スーパーに買(か)い物(もの)に行(い)く。
映(えい)画(が)をスクリーン位(くらい)映(うつ)す。
ステーキを焼(や)く。
スイッチを入()れる。
黒()いスーツを着()る。
スーツケースを持()ち歩()く。
スーパーに買()い物()に行()く。
映()画()をスクリーン位()映()す。
ステーキを焼()く。



スイッチを入()れる。
黒()いスーツを着()る。
スーツケースを持()ち歩()く。
スーパーに買()い物()に行()く。
映()画()をスクリーン位()映()す。
ステーキを焼()く。"""

MIXED_EXPECTED = """オートバイに乗(の)って走(はし)る。
部(へ)屋(や)のカーテンを閉(し)める。
ガスの火(ひ)を強(つよ)くする。
ガソリンの値(ね)段(だん)が上(あ)がる。
近(ちか)くのガソリンスタンドを探(さが)す。
ガラスは壊(こわ)れやすい。
昼(ちゅう)食(しょく)はカレーにする。
キッチンで料(りょう)理(り)をする。
体(たい)重(じゅう)が５キロメートルも増(ふ)えてしまった。
時(じ)速(そく)１００キロメートルで走(はし)る。
ケーキを半(はん)分(ぶん)に切(き)る。
ケースに入(い)れる。
市(し)民(みん)ホールでコンサートが開(ひら)かれた。
を使(つか)ってメールを送(おく)る。
作家(さっか)にサインをもらう。
友(とも)達(だち)とサッカーを見(み)に行(い)く。
野菜(やさい)サラダを食(た)べる。
夏(なつ)はやはりサンダルがいい。
ハムと野菜(やさい)の入(はい)ったサンドイッチを買(か)った。
イチゴジャムを塗(ぬ)って食(た)べる。
オラン時(じ)ジュースを飲(の)む。
スイッチを入(い)れる。
黒(くろ)いスーツを着(き)る。
スーツケースを持(も)ち歩(ある)く。
スーパーに買(か)い物(もの)に行(い)く。
映(えい)画(が)をスクリーン位(くらい)映(うつ)す。
ステーキを焼(や)く。
スイッチを入(い)れる。
黒(くろ)いスーツを着(き)る。
スーツケースを持(も)ち歩(ある)く。
スーパーに買(か)い物(もの)に行(い)く。
映(えい)画(が)をスクリーン位(くらい)映(うつ)す。
ステーキを焼(や)く。



スイッチを入(い)れる。
黒(くろ)いスーツを着(き)る。
スーツケースを持(も)ち歩(ある)く。
スーパーに買(か)い物(もの)に行(い)く。
映(えい)画(が)をスクリーン位(くらい)映(うつ)す。
ステーキを焼(や)く。"""


def test_add_furigana_endpoint_fills_placeholder_only_block() -> None:
    response = client.post("/text/add-furigana", json={"text": PLACEHOLDER_ONLY_INPUT})

    assert response.status_code == 200
    assert response.json() == {
        "original_text": PLACEHOLDER_ONLY_INPUT,
        "result_text": PLACEHOLDER_ONLY_EXPECTED,
    }


def test_add_furigana_endpoint_fills_mixed_block() -> None:
    response = client.post("/text/add-furigana", json={"text": MIXED_INPUT})

    assert response.status_code == 200
    assert response.json() == {
        "original_text": MIXED_INPUT,
        "result_text": MIXED_EXPECTED,
    }


def test_add_furigana_endpoint_returns_hiragana_only_when_requested() -> None:
    response = client.post(
        "/text/add-furigana",
        json={"text": "日本(にほん)へスーパーで行く。", "mode": "hiragana_only"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "original_text": "日本(にほん)へスーパーで行く。",
        "result_text": "にほんへすーぱーでいく。",
    }


def test_add_furigana_endpoint_returns_market_override_in_hiragana_only_mode() -> None:
    response = client.post(
        "/text/add-furigana",
        json={"text": "市場へ行く。", "mode": "hiragana_only"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "original_text": "市場へ行く。",
        "result_text": "いちばへいく。",
    }


def test_add_furigana_endpoint_validates_mode() -> None:
    response = client.post(
        "/text/add-furigana",
        json={"text": "日本", "mode": "invalid"},
    )

    assert response.status_code == 422


def test_remove_furigana_endpoint_removes_brackets_by_default() -> None:
    text = "日本(にほん)へ行く"

    response = client.post("/text/remove-furigana", json={"text": text})

    assert response.status_code == 200
    assert response.json() == {
        "original_text": text,
        "result_text": "日本へ行く",
    }


def test_remove_furigana_endpoint_keeps_empty_brackets_when_requested() -> None:
    text = "日本(にほん)と先生[せんせい]とnote (test)"

    response = client.post(
        "/text/remove-furigana",
        json={"text": text, "remove_brackets": False},
    )

    assert response.status_code == 200
    assert response.json() == {
        "original_text": text,
        "result_text": "日本()と先生[]とnote (test)",
    }


class MockResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")

    def json(self) -> Any:
        return self._payload


def test_vocabulary_batch_endpoint_returns_mixed_statuses(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(url: str, params: dict[str, str], timeout: float) -> MockResponse:
        keyword = params["keyword"]
        if keyword == "猫":
            return MockResponse(
                {
                    "meta": {"status": 200},
                    "data": [
                        {
                            "is_common": True,
                            "japanese": [{"word": "猫", "reading": "ねこ"}],
                            "senses": [
                                {
                                    "english_definitions": ["cat"],
                                    "parts_of_speech": ["Noun"],
                                }
                            ],
                        }
                    ],
                }
            )
        if keyword == "障害":
            return MockResponse({}, status_code=503)
        if keyword == "今日":
            return MockResponse(
                {
                    "meta": {"status": 200},
                    "data": [
                        {
                            "is_common": True,
                            "japanese": [{"word": "今日", "reading": "きょう"}],
                            "senses": [
                                {
                                    "english_definitions": ["today"],
                                    "parts_of_speech": ["Noun"],
                                }
                            ],
                        }
                    ],
                }
            )
        return MockResponse({"meta": {"status": 200}, "data": []})

    monkeypatch.setattr(vocabulary_service.requests, "get", mock_get)

    response = client.post(
        "/text/vocabulary/batch",
        json={"texts": ["猫", "cat", "存在しない単語", "", "障害", "今日"]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "original_texts": ["猫", "cat", "存在しない単語", "", "障害", "今日"],
        "results": [
            {
                "original_text": "猫",
                "status": "ok",
                "entry": {
                    "word": "猫",
                    "reading": "ねこ",
                    "romanized": "neko",
                    "meanings": ["cat"],
                    "part_of_speech": ["Noun"],
                    "is_common": True,
                },
                "error": None,
            },
            {
                "original_text": "cat",
                "status": "invalid_input",
                "entry": None,
                "error": None,
            },
            {
                "original_text": "存在しない単語",
                "status": "not_found",
                "entry": None,
                "error": None,
            },
            {
                "original_text": "",
                "status": "invalid_input",
                "entry": None,
                "error": None,
            },
            {
                "original_text": "障害",
                "status": "upstream_error",
                "entry": None,
                "error": "status=503",
            },
            {
                "original_text": "今日",
                "status": "ok",
                "entry": {
                    "word": "今日",
                    "reading": "きょう",
                    "romanized": "kyou",
                    "meanings": ["today"],
                    "part_of_speech": ["Noun"],
                    "is_common": True,
                },
                "error": None,
            },
        ],
    }


def test_vocabulary_batch_endpoint_validates_payload_size() -> None:
    response = client.post("/text/vocabulary/batch", json={"texts": ["猫"] * 21})

    assert response.status_code == 422


def test_openapi_does_not_include_single_vocabulary_path() -> None:
    app.openapi_schema = None
    schema = app.openapi()

    assert "/text/vocabulary" not in schema["paths"]
    assert "/text/vocabulary/batch" in schema["paths"]
