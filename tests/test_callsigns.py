import random
import re

import pytest

from morse_app.callsigns import (
    generate_chinese_callsign,
    generate_global_callsign,
    is_plausible_callsign,
)


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
