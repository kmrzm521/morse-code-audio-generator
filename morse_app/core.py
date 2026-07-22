"""摩斯电码转换核心。"""

from __future__ import annotations

from dataclasses import dataclass


MORSE_CODES = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
    "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
    "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--",
    "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "!": "-.-.--",
    "/": "-..-.", "=": "-...-", "+": ".-.-.", "(": "-.--.", ")": "-.--.-",
}

SHORT_NUMBERS = {
    "0": "-", "1": ".-", "2": "..-", "3": "...-", "4": "....-",
    "5": ".....", "6": "-....", "7": "-...", "8": "-..", "9": "-.",
}

PROSIGNS = {"AR": ".-.-.", "SK": "...-.-", "BT": "-...-"}


@dataclass(frozen=True, slots=True)
class MorseToken:
    text: str
    code: str


def text_to_tokens(text: str, number_style: str = "long") -> list[MorseToken]:
    """把文本转换为摩斯字符；遇到未知字符时明确报错。"""
    if number_style not in {"long", "short"}:
        raise ValueError("数字编码必须是 long 或 short")

    source = text.upper()
    tokens: list[MorseToken] = []
    index = 0
    while index < len(source):
        if source[index] == "<":
            closing = source.find(">", index + 1)
            if closing != -1:
                name = source[index + 1 : closing]
                if name in PROSIGNS:
                    tokens.append(MorseToken(name, PROSIGNS[name]))
                    index = closing + 1
                    continue

        character = source[index]
        if character.isspace():
            if not tokens or tokens[-1].text != " ":
                tokens.append(MorseToken(" ", "/"))
        elif character.isdigit() and number_style == "short":
            tokens.append(MorseToken(character, SHORT_NUMBERS[character]))
        elif character in MORSE_CODES:
            tokens.append(MorseToken(character, MORSE_CODES[character]))
        else:
            raise ValueError(f"不支持的字符：{character}")
        index += 1

    return tokens
