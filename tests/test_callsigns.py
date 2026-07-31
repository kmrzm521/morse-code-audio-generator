import random
import re
from pathlib import Path

import pytest

from morse_app.callsigns import (
    generate_chinese_callsign,
    generate_global_callsign,
    is_plausible_callsign,
    load_callsigns,
)
from morse_app.callsign_rules import global_entity_names, load_global_rules


@pytest.mark.parametrize(
    "province,digit",
    [("北京", "1"), ("广东", "7"), ("新疆", "0"), ("西藏", "0")],
)
def test_chinese_callsign_uses_official_district(province, digit):
    call = generate_chinese_callsign(province, "G", random.Random(3))
    assert call.startswith(f"BG{digit}")
    assert is_plausible_callsign(call)


def test_chinese_suffix_stays_in_province_range():
    call = generate_chinese_callsign("广东", "H", random.Random(12))
    assert re.fullmatch(r"BH7[I-P][A-Z]{1,2}", call)


def test_chinese_suffix_excludes_reserved_groups():
    for seed in range(500):
        suffix = generate_chinese_callsign("北京", "G", random.Random(seed))[3:]
        assert suffix not in {"SOS", "XXX", "TTT"}
        assert not (len(suffix) == 3 and "QOA" <= suffix <= "QUZ")


def test_rejects_unknown_province_or_station_type():
    with pytest.raises(ValueError, match="省份"):
        generate_chinese_callsign("未知", "G", random.Random(1))
    with pytest.raises(ValueError, match="台站种类"):
        generate_chinese_callsign("北京", "Z", random.Random(1))


@pytest.mark.parametrize(
    "country",
    ["中国", "美国", "日本", "德国", "俄罗斯", "英国", "加拿大", "澳大利亚"],
)
def test_global_generator_returns_plausible_callsign(country):
    call = generate_global_callsign(country, random.Random(11))
    assert is_plausible_callsign(call), call


def test_rejects_unsupported_country():
    with pytest.raises(ValueError, match="国家"):
        generate_global_callsign("未知", random.Random(1))


def test_loads_deduplicated_txt_callsigns(tmp_path: Path):
    path = tmp_path / "calls.txt"
    path.write_text("bg2gnr\n BG2GNR \ninvalid value\nK1ABC\n", encoding="utf-8")
    assert load_callsigns(path) == ["BG2GNR", "K1ABC"]


def test_loads_named_csv_column(tmp_path: Path):
    path = tmp_path / "calls.csv"
    path.write_text("name,callsign\nA,JA1ABC\nB,DL1XYZ\n", encoding="utf-8-sig")
    assert load_callsigns(path) == ["JA1ABC", "DL1XYZ"]


def test_loads_chinese_csv_header(tmp_path: Path):
    path = tmp_path / "calls.csv"
    path.write_text("呼号,备注\nVK2ABC,test\n", encoding="utf-8-sig")
    assert load_callsigns(path) == ["VK2ABC"]


def test_rejects_csv_without_callsign_column(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("name,city\nA,B\n", encoding="utf-8")
    with pytest.raises(ValueError, match="呼号列"):
        load_callsigns(path)


def test_rejects_unsupported_extension(tmp_path: Path):
    path = tmp_path / "calls.xlsx"
    path.write_bytes(b"data")
    with pytest.raises(ValueError, match="TXT.*CSV"):
        load_callsigns(path)


def test_rejects_file_without_usable_callsigns(tmp_path: Path):
    path = tmp_path / "empty.txt"
    path.write_text("not a call\n", encoding="utf-8")
    with pytest.raises(ValueError, match="有效呼号"):
        load_callsigns(path)


def test_global_rules_cover_current_dxcc_entities():
    names = global_entity_names()
    assert len(names) == 340
    assert all(re.search(r"[\u4e00-\u9fff]", name) for name in names)
    assert len(set(names)) == len(names)


def test_global_rules_include_source_version():
    rules = load_global_rules()
    assert rules.version == "2020-02"
    assert "Apache" in rules.license_name


def test_every_entity_generates_ascii_callsign():
    for name in global_entity_names():
        value = generate_global_callsign(name, random.Random(7))
        assert re.fullmatch(r"[A-Z0-9/]+", value), (name, value)


def test_seeded_global_callsign_is_repeatable():
    name = global_entity_names()[20]
    assert generate_global_callsign(name, random.Random(9)) == generate_global_callsign(
        name,
        random.Random(9),
    )
