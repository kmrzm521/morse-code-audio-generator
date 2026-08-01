"""摩斯电码转换核心。"""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from math import cos, pi, sin
from typing import Iterator, Literal


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


@dataclass(frozen=True, slots=True)
class TimingEvent:
    kind: Literal["tone", "silence"]
    start: float
    duration: float
    token_index: int | None = None


def text_to_tokens(text: str, number_style: str = "long") -> list[MorseToken]:
    """把文本转换为摩斯字符；遇到未知字符时明确报错。"""
    if number_style not in {"long", "short"}:
        raise ValueError("数字编码必须选择普通数字或缩短数字")

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


def build_timeline(
    tokens: list[MorseToken],
    character_wpm: float,
    effective_wpm: float | None = None,
) -> list[TimingEvent]:
    """根据 ITU 1:3:7 比例构建音调与静音时间轴。"""
    if character_wpm <= 0:
        raise ValueError("字符速度必须大于 0")
    if effective_wpm is not None and effective_wpm >= character_wpm:
        raise ValueError("间隔降速必须低于字符速度")
    if effective_wpm is not None and effective_wpm <= 0:
        raise ValueError("间隔降速必须大于 0")

    dit = 1.2 / character_wpm
    spacing_unit = dit
    if effective_wpm is not None:
        spacing_unit = (60.0 / effective_wpm - 31.0 * dit) / 19.0

    events: list[TimingEvent] = []
    cursor = 0.0

    def append(kind: Literal["tone", "silence"], duration: float, token_index=None):
        nonlocal cursor
        events.append(TimingEvent(kind, cursor, duration, token_index))
        cursor += duration

    for token_index, token in enumerate(tokens):
        if token.text == " ":
            continue
        for symbol_index, symbol in enumerate(token.code):
            append("tone", dit if symbol == "." else 3.0 * dit, token_index)
            if symbol_index < len(token.code) - 1:
                append("silence", dit)

        next_index = token_index + 1
        saw_space = False
        while next_index < len(tokens) and tokens[next_index].text == " ":
            saw_space = True
            next_index += 1
        if next_index < len(tokens):
            append("silence", (7.0 if saw_space else 3.0) * spacing_unit)

    return events


def render_pcm(
    events: list[TimingEvent],
    frequency: float,
    sample_rate: int = 44_100,
    amplitude: float = 0.8,
) -> bytes:
    """把时间轴渲染为 16 位单声道 PCM，并平滑每段音调的边缘。"""
    return b"".join(
        iter_pcm_chunks(
            events,
            frequency,
            sample_rate=sample_rate,
            amplitude=amplitude,
            chunk_seconds=3600,
        )
    )


def iter_pcm_chunks(
    events: list[TimingEvent],
    frequency: float,
    *,
    sample_rate: int = 44_100,
    amplitude: float = 0.8,
    chunk_seconds: float = 10,
) -> Iterator[bytes]:
    """按固定时长分块渲染 16 位单声道 PCM。"""
    if not 300 <= frequency <= 1200:
        raise ValueError("音调频率必须在 300 至 1200 赫兹之间")
    if sample_rate <= 0:
        raise ValueError("采样率必须大于 0")
    if not 0 < amplitude <= 1:
        raise ValueError("振幅必须大于 0 且不超过 1")
    if chunk_seconds <= 0:
        raise ValueError("音频分块时长必须大于 0")
    if not events:
        return

    total_samples = round((events[-1].start + events[-1].duration) * sample_rate)
    peak = int(32767 * amplitude)
    max_fade_samples = round(sample_rate * 0.005)
    chunk_samples = max(1, round(sample_rate * chunk_seconds))
    tones = [event for event in events if event.kind == "tone"]

    for chunk_start in range(0, total_samples, chunk_samples):
        chunk_end = min(total_samples, chunk_start + chunk_samples)
        samples = array("h", [0]) * (chunk_end - chunk_start)
        for event in tones:
            event_start = round(event.start * sample_rate)
            event_end = round((event.start + event.duration) * sample_rate)
            if event_end <= chunk_start or event_start >= chunk_end:
                continue
            count = max(0, event_end - event_start)
            fade_samples = min(max_fade_samples, count // 2)
            overlap_start = max(event_start, chunk_start)
            overlap_end = min(event_end, chunk_end)
            for sample_index in range(overlap_start, overlap_end):
                offset = sample_index - event_start
                envelope = 1.0
                if fade_samples:
                    edge_distance = min(offset, count - 1 - offset)
                    if edge_distance < fade_samples:
                        envelope = 0.5 - 0.5 * cos(
                            pi * edge_distance / fade_samples
                        )
                value = peak * envelope * sin(
                    2.0 * pi * frequency * offset / sample_rate
                )
                samples[sample_index - chunk_start] = round(value)
        yield samples.tobytes()
