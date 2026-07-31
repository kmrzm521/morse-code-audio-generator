"""加载内置的全球标准模拟呼号规则。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files


@dataclass(frozen=True, slots=True)
class CallsignRule:
    entity_id: int
    entity: str
    prefixes: tuple[str, ...]
    prefix_regex: str


@dataclass(frozen=True, slots=True)
class GlobalCallsignRules:
    version: str
    license_name: str
    source_url: str
    source_note_zh: str
    entities: tuple[CallsignRule, ...]


@lru_cache(maxsize=1)
def load_global_rules() -> GlobalCallsignRules:
    path = files("morse_app.data").joinpath("global_callsign_rules.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entities = tuple(
            CallsignRule(
                entity_id=int(item["id"]),
                entity=str(item["name_zh"]),
                prefixes=tuple(item["prefixes"]),
                prefix_regex=str(item["prefix_regex"]),
            )
            for item in data["entities"]
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("全球呼号规则数据不可用") from error

    names = [rule.entity for rule in entities]
    if len(entities) != 340 or len(names) != len(set(names)):
        raise ValueError("全球呼号规则数据不完整")
    for rule in entities:
        if not rule.prefixes or not all(
            re.fullmatch(r"[A-Z0-9/]+", prefix) for prefix in rule.prefixes
        ):
            raise ValueError("全球呼号规则数据包含无效前缀")
        re.compile(rule.prefix_regex)

    return GlobalCallsignRules(
        version=str(data["version"]),
        license_name=str(data["license_name"]),
        source_url=str(data["source_url"]),
        source_note_zh=str(data["source_note_zh"]),
        entities=entities,
    )


def global_entity_names() -> tuple[str, ...]:
    return tuple(rule.entity for rule in load_global_rules().entities)
