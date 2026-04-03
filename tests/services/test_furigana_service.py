import pytest
import requests

from app.services import furigana_service
from app.services.furigana_service import add_furigana, add_furigana_batch


PLAIN_CASES = [
    ("旅行", "旅(りょ)行(こう)"),
    ("旅行(りょこう)", "旅(りょ)行(こう)"),
    ("アフリカを旅行(りょこう)する。", "アフリカを旅(りょ)行(こう)する。"),
    ("今年(ことし)", "今年(ことし)"),
    ("飲み物", "飲(の)み物(もの)"),
    ("市場", "市(いち)場(ば)"),
    ("先生が生徒を褒める。", "先生(せんせい)が生(せい)徒(と)を褒(ほ)める。"),
]

NEW_PLAIN_CASES = [
    ("オートバイに乗る。", "オートバイに乗(の)る。"),
    ("部屋のカーテンを閉める。", "部(へ)屋(や)のカーテンを閉(し)める。"),
    ("ガスの火を強くする。", "ガスの火(ひ)を強(つよ)くする。"),
    ("ガソリンの値段が上がる。", "ガソリンの値(ね)段(だん)が上(あ)がる。"),
    ("近くのガソリンスタンドを探す。", "近(ちか)くのガソリンスタンドを探(さが)す。"),
    ("ガラスは壊れやすい。", "ガラスは壊(こわ)れやすい。"),
    ("昼食はカレーにする。", "昼(ちゅう)食(しょく)はカレーにする。"),
    ("キッチンで料理をする。", "キッチンで料(りょう)理(り)をする。"),
    ("体重が５キロメートルも増えてしまった。", "体(たい)重(じゅう)が５キロメートルも増(ふ)えてしまった。"),
    ("時速１００キロメートルで走る。", "時(じ)速(そく)１００キロメートルで走(はし)る。"),
    ("ケーキを半分に切る。", "ケーキを半(はん)分(ぶん)に切(き)る。"),
    ("ケースに入れる。", "ケースに入(い)れる。"),
    ("市民ホールでコンサートが開かれた。", "市(し)民(みん)ホールでコンサートが開(ひら)かれた。"),
    ("パソコンを使ってメールを送る。", "パソコンを使(つか)ってメールを送(おく)る。"),
    ("作家にサインをもらう。", "作家(さっか)にサインをもらう。"),
    ("友達とサッカーを見に行く。", "友(とも)達(だち)とサッカーを見(み)に行(い)く。"),
    ("野菜サラダを食べる。", "野菜(やさい)サラダを食(た)べる。"),
    ("夏はやはりサンダルがいい。", "夏(なつ)はやはりサンダルがいい。"),
    ("ハムと野菜の入ったサンドイッチを買った。", "ハムと野菜(やさい)の入(はい)ったサンドイッチを買(か)った。"),
    ("イチゴジャムを塗って食べる。", "イチゴジャムを塗(ぬ)って食(た)べる。"),
    ("オレンジジュースを飲む。", "オレンジジュースを飲(の)む。"),
    ("映画をスクリーンに映す。", "映(えい)画(が)をスクリーンに映(うつ)す。"),
]


PLACEHOLDER_CASES = [
    ("がんばった。けれども、失()敗()した。", "がんばった。けれども、失(しっ)敗(ぱい)した。"),
    ("天()気()は悪()い。しかし、出()かける。", "天(てん)気(き)は悪(わる)い。しかし、出(で)かける。"),
    ("ドアをノックした。すると誰()か出()てきた。", "ドアをノックした。すると誰(だれ)か出(で)てきた。"),
    (
        "中()学()校()を卒()業()して、そして、高()校()に入()学()した。",
        "中(ちゅう)学(がっ)校(こう)を卒(そつ)業(ぎょう)して、そして、高(こう)校(こう)に入(にゅう)学(がく)した。",
    ),
    ("顔()を洗()って、それからご飯()を食()べる。", "顔(かお)を洗(あら)って、それからご飯(はん)を食(た)べる。"),
    (
        "昨日()は電()気()が悪()かった。それで出()かけなかった。",
        "昨日(きのう)は電(でん)気(き)が悪(わる)かった。それで出(で)かけなかった。",
    ),
    ("それでは始()めましょう。", "それでは始(はじ)めましょう。"),
    ("この仕()事()は楽()だ。それに給()料()もいい。", "この仕(し)事(ごと)は楽(らく)だ。それに給(きゅう)料(りょう)もいい。"),
    ("もう時()間()がない。だから急()がなければならない。", "もう時(じ)間(かん)がない。だから急(いそ)がなければならない。"),
    ("電()話()またはメールで知()らせます。", "電(でん)話(わ)またはメールで知(し)らせます。"),
    ("いいアイデアを出()す。", "いいアイデアを出(だ)す。"),
    ("アイロンをかける。", "アイロンをかける。"),
    ("アクセサリーをつける。", "アクセサリーをつける。"),
    ("アジアには多()くの国()がある。", "アジアには多(おお)くの国(くに)がある。"),
    ("アナウンサーがニュースを読()む。", "アナウンサーがニュースを読(よ)む。"),
    ("テレビでアニメを見()る。", "テレビでアニメを見(み)る。"),
    ("アフリカを旅()行()する。", "アフリカを旅(りょ)行(こう)する。"),
    ("アメリカに留()学()に行()く。", "アメリカに留(りゅう)学(がく)に行(い)く。"),
    ("この飲()み物()にはアルコールが入()っている。", "この飲(の)み物(もの)にはアルコールが入(はい)っている。"),
    ("本()屋()でアルバイトをする。", "本(ほん)屋(や)でアルバイトをする。"),
    ("イヤリングをつける。", "イヤリングをつける。"),
    ("エアコンが壊()れている。", "エアコンが壊(こわ)れている。"),
    ("四()階()まではエスカレーターで上()がる。", "四(よん)階(かい)まではエスカレーターで上(あ)がる。"),
]

NEW_PLACEHOLDER_CASES = [
    ("先()生()が来る。", "先生(せんせい)が来(く)る。"),
    ("今()年()は暑い。", "今年(ことし)は暑(あつ)い。"),
    ("電()車()に乗る。", "電(でん)車(しゃ)に乗(の)る。"),
    ("日()本()へ行く。", "日(にっ)本(ぽん)へ行(い)く。"),
    ("スイッチを入()れる。", "スイッチを入(い)れる。"),
    ("黒()いスーツを着()る。", "黒(くろ)いスーツを着(き)る。"),
    ("スーツケースを持()ち歩()く。", "スーツケースを持(も)ち歩(ある)く。"),
    ("スーパーに買()い物()に行()く。", "スーパーに買(か)い物(もの)に行(い)く。"),
    ("映画をスクリーンに映()す。", "映(えい)画(が)をスクリーンに映(うつ)す。"),
    ("ステーキを焼()く。", "ステーキを焼(や)く。"),
]

HIRAGANA_ONLY_CASES = [
    ("日本", "にほん"),
    ("日本へ行く。", "にほんへいく。"),
    ("スーパー", "すーぱー"),
    ("市場", "いちば"),
    ("ABC日本123", "ABCにほん123"),
    ("日本(にほん)", "にほん"),
    ("日()本()", "にほん"),
    ("株式市場", "かぶしきしじょう"),
    ("note (test)", "note (test)"),
]


@pytest.mark.parametrize(
    ("text", "expected"),
    PLAIN_CASES + NEW_PLAIN_CASES + PLACEHOLDER_CASES + NEW_PLACEHOLDER_CASES,
)
def test_add_furigana(text: str, expected: str) -> None:
    assert add_furigana(text) == expected


@pytest.mark.parametrize(("text", "expected"), HIRAGANA_ONLY_CASES)
def test_add_furigana_hiragana_only(text: str, expected: str) -> None:
    assert add_furigana(text, mode="hiragana_only") == expected


def test_add_furigana_batch_preserves_order_and_matches_single_item_results() -> None:
    texts = ["旅行", "市場", "旅行(りょこう)", ""]

    results = add_furigana_batch(texts)

    assert [item.original_text for item in results] == texts
    assert [item.result_text for item in results] == [add_furigana(text) for text in texts]


def test_add_furigana_batch_hiragana_only_matches_single_item_results() -> None:
    texts = ["日本", "市場へ行く。", "スーパー", "ABC123", ""]

    results = add_furigana_batch(texts, mode="hiragana_only")

    assert [item.original_text for item in results] == texts
    assert [item.result_text for item in results] == [add_furigana(text, mode="hiragana_only") for text in texts]


class MockYomiResponse:
    status_code = 200

    def __init__(self, words: list[dict]) -> None:
        self._words = words

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"text": "", "converted": "", "words": self._words}


def test_add_furigana_uses_yomi_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    """Yomi's pronunciation_raw is preferred over the local cutlet reading."""
    yomi_words = [
        {"surface": "東京", "pronunciation_raw": "トウキョウ"},
        {"surface": "都", "pronunciation_raw": "ト"},
    ]

    monkeypatch.setattr(
        furigana_service.requests,
        "post",
        lambda *args, **kwargs: MockYomiResponse(yomi_words),
    )

    # Yomi returns トウキョウ for 東京 → split into 東(とう)京(きょう), and ト for 都 → 都(と)
    result = add_furigana("東京都")

    assert result == "東(とう)京(きょう)都(と)"


def test_add_furigana_falls_back_on_yomi_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A network error from Yomi causes silent fallback to the local reading."""
    def raise_error(*args, **kwargs) -> None:
        raise requests.RequestException("timeout")

    monkeypatch.setattr(furigana_service.requests, "post", raise_error)

    # Local pipeline still produces a valid result
    result = add_furigana("旅行")
    assert result == "旅(りょ)行(こう)"


def test_add_furigana_falls_back_when_yomi_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """When YOMI_ENABLED=False the local pipeline is used without any HTTP call."""
    called = []

    def should_not_be_called(*args, **kwargs) -> None:
        called.append(True)

    monkeypatch.setattr(furigana_service.requests, "post", should_not_be_called)
    monkeypatch.setattr(furigana_service.settings, "YOMI_ENABLED", False)

    result = add_furigana("旅行")

    assert called == []
    assert result == "旅(りょ)行(こう)"


def test_add_furigana_skips_yomi_for_long_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Texts over 5000 characters skip the Yomi API and use the local pipeline."""
    called = []

    def should_not_be_called(*args, **kwargs) -> None:
        called.append(True)

    monkeypatch.setattr(furigana_service.requests, "post", should_not_be_called)
    monkeypatch.setattr(furigana_service.settings, "YOMI_ENABLED", True)

    long_text = "旅行" * 2501  # > 5000 chars
    add_furigana(long_text)

    assert called == []
