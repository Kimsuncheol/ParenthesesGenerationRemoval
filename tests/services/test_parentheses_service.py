import pytest

from app.services.parentheses_service import generate_parentheses, remove_equal_sign, remove_parentheses

# fmt: off
SAMPLE_CASES = [
    (
        "電(でん)車(しゃ)の中(なか)で足(あし)を踏(ふ)まれた。",
        "電車の中で足を踏まれた。",
    ),
    (
        "先(せん)生(せい)が生(せい)徒(と)を褒(ほ)める。",
        "先生が生徒を褒める。",
    ),
    (
        "明(あし)日(た)また参(まい)ります。",
        "明日また参ります。",
    ),
    (
        "試(し)合(あい)に負(あ)ける。",
        "試合に負ける。",
    ),
    (
        "答(こた)えを間(ま)違(ちが)える。",
        "答えを間違える。",
    ),
    (
        "会(かい)議(ぎ)の時(じ)間(かん)に間(ま)に合(あ)う。",
        "会議の時間に間に合う。",
    ),
    (
        "有(ゆう)名(めい)なところを見(み)て回(まわ)る。",
        "有名なところを見て回る。",
    ),
    (
        "窓(まど)がら海(うみ)が見(み)える。",
        "窓がら海が見える。",
    ),
    (
        "いい方(ほう)法(ほう)が見(み)つかる。",
        "いい方法が見つかる。",
    ),
    (
        "落(おと)とし物(もの)を見(み)つける。",
        "落とし物を見つける。",
    ),
    (
        "何(なに)を召(め)し上(あ)がりますか。",
        "何を召し上がりますか。",
    ),
    (
        "ご説(せつ)明(めい)申(もう)し上(あ)げます。",
        "ご説明申し上げます。",
    ),
    (
        "私(わたし)は中(なか)山(やま)と申(もう)します。",
        "私は中山と申します。",
    ),
    (
        "本(ほん)を本(本)棚(だな)に戻(もど)す。",
        "本を本棚に戻す。",
    ),
]
# fmt: on


@pytest.mark.parametrize("text, expected", SAMPLE_CASES)
def test_remove_parentheses_furigana(text: str, expected: str) -> None:
    assert remove_parentheses(text) == expected


# fmt: off
GENERATE_CASES = [
    (
        "電車の中で足を踏まれた。",
        "電()車()の中()で足()を踏()まれた。",
    ),
    (
        "先生が生徒を褒める。",
        "先()生()が生()徒()を褒()める。",
    ),
    (
        "明日また参ります。",
        "明()日()また参()ります。",
    ),
    (
        "試合に負ける。",
        "試()合()に負()ける。",
    ),
    (
        "答えを間違える。",
        "答()えを間()違()える。",
    ),
    (
        "私は中山と申します。",
        "私()は中()山()と申()します。",
    ),
    (
        "本を本棚に戻す。",
        "本()を本()棚()に戻()す。",
    ),
    (
        "いい方法が見つかる。",
        "いい方()法()が見()つかる。",
    ),
    # numbers: fullwidth digits
    (
        "テキストの３５ページを平手ください。",
        "テキストの３()５()ページを平()手()ください。",
    ),
    # numbers: ASCII digits
    (
        "35ページを読む。",
        "3()5()ページを読()む。",
    ),
    # numbers: mixed fullwidth and ASCII
    (
        "問題１2を解く。",
        "問()題()１()2()を解()く。",
    ),
    # list-marker digit: single item
    (
        "1. 冷たいジュースを飲む。",
        "1. 冷()たいジュースを飲()む。",
    ),
    # list-marker digits: two items
    (
        "1. 冷たいジュースを飲む。2. 田中さんは冷たい人です。",
        "1. 冷()たいジュースを飲()む。2. 田()中()さんは冷()たい人()です。",
    ),
]
# fmt: on


@pytest.mark.parametrize("text, expected", GENERATE_CASES)
def test_generate_parentheses(text: str, expected: str) -> None:
    assert generate_parentheses(text) == expected


_MULTI_LEFT_INPUT = "終える = to finish\n行う = to carry out\n起こる = to happen\nおごる = to treat\n教わる = to be taught\n落ち着く = to calm down\n驚かす = to surprise"
_MULTI_LEFT_OUTPUT = "to finish\nto carry out\nto happen\nto treat\nto be taught\nto calm down\nto surprise"

_MULTI_RIGHT_INPUT = "終える = to finish\n行う = to carry out\n起こる = to happen\nおごる = to treat\n教わる = to be taught\n落ち着く = to calm down\n驚かす = to surprise"
_MULTI_RIGHT_OUTPUT = "終える\n行う\n起こる\nおごる\n教わる\n落ち着く\n驚かす"

_MULTI_SPECIAL_LEFT_INPUT = "* 終える = to finish\n* 行う = to carry out\n* 起こる = to happen\n* おごる = to treat\n* 教わる = to be taught\n* 落ち着く = to calm down\n* 驚かす = to surprise"
_MULTI_SPECIAL_RIGHT_KEEP = "* 終える\n* 行う\n* 起こる\n* おごる\n* 教わる\n* 落ち着く\n* 驚かす"
_MULTI_SPECIAL_RIGHT_STRIP = "終える\n行う\n起こる\nおごる\n教わる\n落ち着く\n驚かす"

# fmt: off
REMOVE_EQUAL_SIGN_CASES = [
    # (text, remove_side, strip_leading_specials, expected)

    # ── remove_side="left" (case 1: single line, no specials) ──────────────
    ("終える = to finish",          "left",  False, "to finish"),
    ("犬 = dog",                    "left",  False, "dog"),
    ("食べる=to eat",               "left",  False, "to eat"),

    # ── remove_side="left" (case 2: multi-line, no specials) ───────────────
    (_MULTI_LEFT_INPUT,             "left",  False, _MULTI_LEFT_OUTPUT),

    # ── remove_side="left" (case 3: single line with leading specials) ─────
    # specials are on the left → naturally discarded with the left side
    ("* 終える = to finish",        "left",  False, "to finish"),
    ("- 犬 = dog",                  "left",  False, "dog"),

    # ── remove_side="left" (case 4: multi-line with leading specials) ──────
    (_MULTI_SPECIAL_LEFT_INPUT,     "left",  False, _MULTI_LEFT_OUTPUT),

    # ── remove_side="right" (case 1: single line, no specials) ────────────
    ("終える = to finish",          "right", False, "終える"),
    ("犬 = dog",                    "right", False, "犬"),
    ("食べる=to eat",               "right", False, "食べる"),

    # ── remove_side="right" (case 2: multi-line, no specials) ─────────────
    (_MULTI_RIGHT_INPUT,            "right", False, _MULTI_RIGHT_OUTPUT),

    # ── remove_side="right" (case 3/4: with leading specials, keep) ────────
    ("* 終える = to finish",        "right", False, "* 終える"),
    (_MULTI_SPECIAL_LEFT_INPUT,     "right", False, _MULTI_SPECIAL_RIGHT_KEEP),

    # ── remove_side="right" (case 3/4: with leading specials, strip) ───────
    ("* 終える = to finish",        "right", True,  "終える"),
    ("** 食べる = to eat",          "right", True,  "食べる"),
    (_MULTI_SPECIAL_LEFT_INPUT,     "right", True,  _MULTI_SPECIAL_RIGHT_STRIP),

    # ── no equal sign — return line/text unchanged ─────────────────────────
    ("終える",                      "left",  False, "終える"),
    ("終える",                      "right", False, "終える"),
]
# fmt: on


@pytest.mark.parametrize("text, remove_side, strip_leading_specials, expected", REMOVE_EQUAL_SIGN_CASES)
def test_remove_equal_sign(text: str, remove_side: str, strip_leading_specials: bool, expected: str) -> None:
    assert remove_equal_sign(text, remove_side, strip_leading_specials) == expected  # type: ignore[arg-type]
