import re
from typing import Literal

_OPEN_BRACKETS = set("([{<")
_BRACKET_PAIRS = {"(": ")", "[": "]", "{": "}", "<": ">"}
_CLOSE_BRACKETS = set(_BRACKET_PAIRS.values())

# Matches digits+. that form a list marker, at start of text or right after 。
_LIST_MARKER_RE = re.compile(r'(?:^|(?<=。))([0-9]+)\.')

# Strips leading characters that are not letters, digits, or Japanese script
_LEADING_SPECIAL_RE = re.compile(
    r'^[^\u3040-\u30FF\u4E00-\u9FFF\u3400-\u4DBF\uFF10-\uFF19a-zA-Z0-9]+'
)

# Characters recognized as splitters (first occurrence in a line is used)
_SPLITTER_CHARS = frozenset('=-:;,./()[]{}"\'*')

# Maps an opening bracket splitter to its expected closing bracket
_CLOSING_BRACKET = {"(": ")", "[": "]", "{": "}"}


def _needs_parentheses(char: str) -> bool:
    cp = ord(char)
    return (
        0x4E00 <= cp <= 0x9FFF  # CJK Unified Ideographs (common kanji)
        or 0x3400 <= cp <= 0x4DBF  # CJK Extension A (rare/archaic kanji)
        or 0x0030 <= cp <= 0x0039  # ASCII digits 0-9
        or 0xFF10 <= cp <= 0xFF19  # Fullwidth digits ０-９
    )


def _list_marker_indices(text: str) -> set[int]:
    protected: set[int] = set()
    for m in _LIST_MARKER_RE.finditer(text):
        protected.update(range(m.start(1), m.end(1)))
    return protected


def generate_parentheses(text: str) -> str:
    protected = _list_marker_indices(text)
    result: list[str] = []
    for i, char in enumerate(text):
        result.append(char)
        if _needs_parentheses(char) and i not in protected:
            result.append("()")
    return "".join(result)


def _find_splitter(line: str) -> int:
    for i, ch in enumerate(line):
        if ch in _SPLITTER_CHARS:
            return i
    return -1


def _remove_equal_sign_line(
    line: str, remove_side: Literal["left", "right"], strip_leading_specials: bool
) -> str:
    idx = _find_splitter(line)
    if idx == -1:
        return line
    splitter_char = line[idx]
    if remove_side == "left":
        right = line[idx + 1 :].strip()
        closing = _CLOSING_BRACKET.get(splitter_char)
        if closing and right.endswith(closing):
            right = right[:-1].strip()
        return right
    else:
        left = line[:idx].strip()
        if strip_leading_specials:
            left = _LEADING_SPECIAL_RE.sub("", left)
        return left


def remove_equal_sign(
    text: str,
    remove_side: Literal["left", "right"],
    strip_leading_specials: bool = False,
) -> str:
    lines = text.split("\n")
    return "\n".join(
        _remove_equal_sign_line(line, remove_side, strip_leading_specials)
        for line in lines
    )


def remove_parentheses(text: str) -> str:
    stack: list[str] = []
    result: list[str] = []

    for char in text:
        if char in _OPEN_BRACKETS:
            stack.append(_BRACKET_PAIRS[char])
        elif stack and char == stack[-1]:
            stack.pop()
        elif char in _CLOSE_BRACKETS:
            pass  # unmatched closing bracket — ignore
        elif not stack:
            result.append(char)

    return "".join(result)
