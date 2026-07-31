"""把开放许可的 DXCC 快照转换为程序使用的离线中文规则数据。"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(
    source_path: Path,
    territories_path: Path,
    output_path: Path,
    *,
    expected_count: int = 340,
) -> None:
    source = _load(source_path)
    cldr = _load(territories_path)
    territories = cldr["main"]["zh-Hans"]["localeDisplayNames"]["territories"]
    territories["XI"] = "北爱尔兰"

    current = [item for item in source["dxcc"] if not item["deleted"]]
    country_counts = Counter(item["countryCode"] for item in current)
    entities = []
    for item in current:
        prefixes = [
            value.strip()
            for value in item["prefix"].split(",")
            if re.fullmatch(r"[A-Z0-9/]+", value.strip())
        ]
        if int(item["entityCode"]) == 247:
            prefixes = ["1S"]
            territory = "南沙群岛"
        else:
            territory = territories[item["countryCode"]]
        if not prefixes:
            raise ValueError(f"实体没有可用前缀：{item['name']}")
        if country_counts[item["countryCode"]] == 1:
            display_name = territory
        else:
            display_name = f"{territory}（{prefixes[0]}）"
        entities.append(
            {
                "id": int(item["entityCode"]),
                "name_zh": display_name,
                "prefixes": prefixes,
                "prefix_regex": item["prefixRegex"],
            }
        )

    name_counts = Counter(item["name_zh"] for item in entities)
    for entity in entities:
        if name_counts[entity["name_zh"]] > 1:
            entity["name_zh"] = (
                f"{entity['name_zh'][:-1]}，实体{entity['id']}）"
            )

    names = [item["name_zh"] for item in entities]
    if len(entities) != expected_count or len(names) != len(set(names)):
        raise ValueError("转换后的现行实体数量或中文名称不正确")

    output = {
        "version": "2020-02",
        "license_name": "Apache-2.0",
        "source_url": "https://github.com/k0swe/dxcc-json",
        "source_note_zh": "全球实体与前缀来自 dxcc-json 的 2020 年 2 月开放许可快照，仅用于标准模拟呼号，不代表真实签发。",
        "entities": sorted(entities, key=lambda item: item["name_zh"]),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("territories", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.source, args.territories, args.output)


if __name__ == "__main__":
    main()
