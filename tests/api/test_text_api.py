import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from main import app
from app.services import vocabulary_service

client = TestClient(app)
VOCABULARY_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "vocabulary_entries.json"


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


@pytest.fixture(autouse=True)
def use_fixture_dictionary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vocabulary_service, "VOCABULARY_DATA_PATH", VOCABULARY_FIXTURE_PATH)
    vocabulary_service._load_dictionary.cache_clear()
    yield
    vocabulary_service._load_dictionary.cache_clear()


def test_vocabulary_endpoint_returns_best_match() -> None:
    response = client.post("/text/vocabulary", json={"text": "猫"})

    assert response.status_code == 200
    assert response.json() == {
        "original_text": "猫",
        "entry": {
            "word": "猫",
            "reading": "ねこ",
            "romanized": "neko",
            "meanings": ["cat"],
            "part_of_speech": ["noun"],
            "is_common": True,
        },
    }


def test_vocabulary_endpoint_returns_null_entry_for_no_match() -> None:
    response = client.post("/text/vocabulary", json={"text": "cat"})

    assert response.status_code == 200
    assert response.json() == {
        "original_text": "cat",
        "entry": None,
    }


def test_vocabulary_endpoint_validates_payload() -> None:
    response = client.post("/text/vocabulary", json={"query": "猫"})

    assert response.status_code == 422
