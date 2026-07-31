"""离线呼号规则与格式校验。"""

from __future__ import annotations

import csv
import random
import re
import string
from pathlib import Path

from .callsign_rules import CallsignRule, load_global_rules


# 工信部《业余无线电台呼号编制和核发要求》（设计基线：2024）。
# 值为：分区号、后缀首字母下限、后缀首字母上限。
CHINA_PROVINCE_RANGES = {
    "北京": ("1", "A", "X"),
    "黑龙江": ("2", "A", "H"), "吉林": ("2", "I", "P"), "辽宁": ("2", "Q", "X"),
    "天津": ("3", "A", "F"), "内蒙古": ("3", "G", "L"),
    "河北": ("3", "M", "R"), "山西": ("3", "S", "X"),
    "上海": ("4", "A", "H"), "山东": ("4", "I", "P"), "江苏": ("4", "Q", "X"),
    "浙江": ("5", "A", "H"), "江西": ("5", "I", "P"), "福建": ("5", "Q", "X"),
    "安徽": ("6", "A", "H"), "河南": ("6", "I", "P"), "湖北": ("6", "Q", "X"),
    "湖南": ("7", "A", "H"), "广东": ("7", "I", "P"),
    "广西": ("7", "Q", "X"), "海南": ("7", "Y", "Z"),
    "四川": ("8", "A", "F"), "重庆": ("8", "G", "L"),
    "贵州": ("8", "M", "R"), "云南": ("8", "S", "X"),
    "陕西": ("9", "A", "F"), "甘肃": ("9", "G", "L"),
    "宁夏": ("9", "M", "R"), "青海": ("9", "S", "X"),
    "新疆": ("0", "A", "F"), "西藏": ("0", "G", "L"),
}

CHINA_STATION_TYPES = frozenset("GHIDABCEFKLR")
RESERVED_SUFFIXES = frozenset({"SOS", "XXX", "TTT"})

COUNTRY_PATTERNS = {
    "中国": re.compile(r"B[GHIDABCEFKLR][0-9][A-Z]{2,3}"),
    "美国": re.compile(r"(?:[KNW]|A[A-L])[0-9][A-Z]{1,3}"),
    "日本": re.compile(r"(?:J[A-S]|7[J-N])[0-9][A-Z]{1,3}"),
    "德国": re.compile(r"D[A-R][0-9][A-Z]{1,3}"),
    "俄罗斯": re.compile(r"(?:R|U[A-Z])[0-9][A-Z]{2,3}"),
    "英国": re.compile(r"(?:[GM][0-9]|2E[0-9])[A-Z]{2,3}"),
    "加拿大": re.compile(r"(?:V[A-G]|V[OY])[0-9][A-Z]{2,3}"),
    "澳大利亚": re.compile(r"VK[0-9][A-Z]{2,3}"),
}

_COUNTRY_ENTITY_IDS = {
    "美国": 291,
    "日本": 339,
    "德国": 230,
    "俄罗斯": 54,
    "英国": 223,
    "加拿大": 1,
    "澳大利亚": 150,
}


def _letters(rng: random.Random, length: int) -> str:
    return "".join(rng.choices(string.ascii_uppercase, k=length))


def _valid_chinese_suffix(suffix: str) -> bool:
    return (
        suffix not in RESERVED_SUFFIXES
        and not (len(suffix) == 3 and "QOA" <= suffix <= "QUZ")
    )


def generate_chinese_callsign(
    province: str,
    station_type: str,
    rng: random.Random,
) -> str:
    """按省级区段生成仅供训练的模拟中国呼号。"""
    if province not in CHINA_PROVINCE_RANGES:
        raise ValueError(f"不支持的省份：{province}")
    station_type = station_type.upper()
    if station_type not in CHINA_STATION_TYPES:
        raise ValueError(f"不支持的台站种类：{station_type}")

    district, first_min, first_max = CHINA_PROVINCE_RANGES[province]
    first_letters = string.ascii_uppercase[
        string.ascii_uppercase.index(first_min) : string.ascii_uppercase.index(first_max) + 1
    ]
    while True:
        length = rng.choice((2, 3))
        suffix = rng.choice(first_letters) + _letters(rng, length - 1)
        if _valid_chinese_suffix(suffix):
            return f"B{station_type}{district}{suffix}"


def generate_global_callsign(country: str, rng: random.Random) -> str:
    """按开放许可的全球实体前缀快照生成标准模拟呼号。"""
    if country == "中国":
        return generate_chinese_callsign(rng.choice(list(CHINA_PROVINCE_RANGES)), "G", rng)

    rules = load_global_rules().entities
    selected: CallsignRule | None = next(
        (rule for rule in rules if rule.entity == country),
        None,
    )
    if selected is None and country in _COUNTRY_ENTITY_IDS:
        expected_id = _COUNTRY_ENTITY_IDS[country]
        selected = next(
            (
                rule
                for rule in rules
                if rule.entity_id == expected_id
            ),
            None,
        )
    if selected is None:
        raise ValueError(f"不支持的国家：{country}")

    prefix = rng.choice(selected.prefixes)
    digit = "" if any(character.isdigit() for character in prefix) else str(rng.randrange(10))
    suffix = _letters(rng, rng.choice((2, 3)))
    return f"{prefix}{digit}{suffix}"


def is_plausible_callsign(value: str) -> bool:
    """检查是否符合任一内置前缀规则；不证明呼号真实存在。"""
    normalized = value.strip().upper()
    if any(pattern.fullmatch(normalized) is not None for pattern in COUNTRY_PATTERNS.values()):
        return True
    return any(
        re.fullmatch(rule.prefix_regex, normalized) is not None
        for rule in load_global_rules().entities
    )


def load_callsigns(path: Path) -> list[str]:
    """从本地 TXT 或 CSV 导入、过滤并去重呼号。"""
    path = Path(path)
    extension = path.suffix.lower()
    if extension not in {".txt", ".csv"}:
        raise ValueError("呼号表只支持 TXT 或 CSV 文件")

    if extension == ".txt":
        candidates = path.read_text(encoding="utf-8-sig").splitlines()
    else:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            headers = reader.fieldnames or []
            header_map = {header.strip().lower(): header for header in headers}
            source_header = next(
                (header_map[name] for name in ("callsign", "call", "呼号") if name in header_map),
                None,
            )
            if source_header is None:
                raise ValueError("CSV 文件中找不到 callsign、call 或呼号列")
            candidates = [row.get(source_header, "") for row in reader]

    result: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip().upper()
        if normalized not in seen and is_plausible_callsign(normalized):
            seen.add(normalized)
            result.append(normalized)
    if not result:
        raise ValueError("文件中没有可用的有效呼号")
    return result
