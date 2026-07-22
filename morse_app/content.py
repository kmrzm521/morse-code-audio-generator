"""听抄练习内容生成。"""

from __future__ import annotations

import random
import string

from .core import build_timeline, text_to_tokens


Q_CODES = ("QRA", "QRG", "QRL", "QRM", "QRN", "QRO", "QRP", "QRQ", "QRS", "QRT", "QRV", "QRZ", "QSB", "QSL", "QSO", "QSY", "QTH")
PROSIGNS = ("<AR>", "<SK>", "<BT>")
PUNCTUATION = ".,?!/+=()"


def generate_group(mode: str, group_size: int, rng: random.Random) -> str:
    if group_size <= 0:
        raise ValueError("每组字符数必须大于 0")
    alphabets = {
        "letters": string.ascii_uppercase,
        "numbers": string.digits,
        "mixed": string.ascii_uppercase + string.digits,
        "punctuation": PUNCTUATION,
    }
    if mode in alphabets:
        return "".join(rng.choices(alphabets[mode], k=group_size))
    if mode == "prosigns":
        return " ".join(rng.choices(PROSIGNS, k=group_size))
    if mode == "q_codes":
        return " ".join(rng.choices(Q_CODES, k=group_size))
    raise ValueError(f"不支持的内容类型：{mode}")


def generate_until_duration(
    mode: str,
    group_size: int,
    target_seconds: float,
    timing_options: dict,
    rng: random.Random,
) -> str:
    """追加完整组，直到总时长首次达到或超过目标。"""
    if target_seconds <= 0:
        raise ValueError("生成时长必须大于 0")
    groups: list[str] = []
    while True:
        groups.append(generate_group(mode, group_size, rng))
        text = " ".join(groups)
        tokens = text_to_tokens(text, timing_options.get("number_style", "long"))
        events = build_timeline(
            tokens,
            timing_options["character_wpm"],
            timing_options.get("effective_wpm"),
        )
        duration = events[-1].start + events[-1].duration if events else 0.0
        if duration >= target_seconds:
            return text
