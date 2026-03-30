_OPEN_BRACKETS = set("([{<")
_BRACKET_PAIRS = {"(": ")", "[": "]", "{": "}", "<": ">"}
_CLOSE_BRACKETS = set(_BRACKET_PAIRS.values())


def _is_kanji(char: str) -> bool:
    cp = ord(char)
    return 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF


def generate_parentheses(text: str) -> str:
    result: list[str] = []
    for char in text:
        result.append(char)
        if _is_kanji(char):
            result.append("()")
    return "".join(result)


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
