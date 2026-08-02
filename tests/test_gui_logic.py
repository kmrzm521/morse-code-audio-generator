from pathlib import Path

import pytest

from morse_app.callsign_rules import global_entity_names
from morse_app.gui import (
    MEMBERSHIP_EMAIL,
    MEMBERSHIP_GUIDE,
    NUMBER_STYLE_LABELS,
    OUTPUT_FORMAT_LABELS,
    PROJECT_URL,
    RANDOM_GLOBAL_ENTITY,
    build_generation_request,
)


def valid_form_values(tmp_path: Path) -> dict[str, object]:
    return {
        "mode": "letters",
        "group_size": "5",
        "duration_seconds": "5",
        "character_wpm": "15",
        "farnsworth_enabled": False,
        "effective_wpm": "10",
        "frequency_hz": "700",
        "number_style": "长码",
        "output_format": "MP3",
        "output_dir": str(tmp_path),
        "province": "北京",
        "country": "中国",
        "station_type": "G",
        "custom_text": "",
    }


def test_custom_mode_requires_text(tmp_path: Path):
    values = valid_form_values(tmp_path) | {"mode": "custom", "custom_text": " "}
    with pytest.raises(ValueError, match="自定义文本不能为空"):
        build_generation_request(values)


def test_simulated_callsign_is_labeled(tmp_path: Path):
    request = build_generation_request(
        valid_form_values(tmp_path) | {"mode": "chinese_callsign"}
    )
    assert request.export.simulated_callsign is True
    assert request.text


def test_random_letters_are_not_labeled_as_callsign(tmp_path: Path):
    request = build_generation_request(valid_form_values(tmp_path))
    assert request.export.simulated_callsign is False
    assert request.export.output_format == "mp3"


def test_non_member_cannot_generate_more_than_five_minutes(tmp_path: Path):
    values = valid_form_values(tmp_path) | {"duration_seconds": "301"}
    with pytest.raises(ValueError, match="永久会员"):
        build_generation_request(values, is_member=False)


def test_member_can_generate_more_than_five_minutes(tmp_path: Path):
    values = valid_form_values(tmp_path) | {
        "mode": "custom",
        "custom_text": "CQ",
        "duration_seconds": "301",
    }
    request = build_generation_request(values, is_member=True)
    assert request.text == "CQ"


def test_rejects_non_numeric_speed(tmp_path: Path):
    values = valid_form_values(tmp_path) | {"character_wpm": "fast"}
    with pytest.raises(ValueError, match="数字"):
        build_generation_request(values)


def test_requires_output_directory(tmp_path: Path):
    values = valid_form_values(tmp_path) | {"output_dir": ""}
    with pytest.raises(ValueError, match="输出目录"):
        build_generation_request(values)


def test_custom_mode_preserves_complete_input(tmp_path: Path):
    values = valid_form_values(tmp_path) | {
        "mode": "custom",
        "custom_text": "CQ CQ DE BG2GNR",
        "duration_seconds": "5",
    }
    request = build_generation_request(values)
    assert request.text == "CQ CQ DE BG2GNR"


def test_chinese_display_values_map_to_internal_codes(tmp_path: Path):
    request = build_generation_request(valid_form_values(tmp_path))
    assert request.export.number_style == "long"
    assert request.export.output_format == "mp3"


def test_display_choices_use_requested_labels():
    labels = tuple(NUMBER_STYLE_LABELS) + tuple(OUTPUT_FORMAT_LABELS)
    assert labels == ("长码", "短码", "MP3", "WAV")


@pytest.mark.parametrize(
    ("number_label", "format_label", "expected_number", "expected_format"),
    [
        ("普通数字", "压缩音频", "long", "mp3"),
        ("缩短数字", "波形音频", "short", "wav"),
    ],
)
def test_old_display_choices_remain_compatible(
    tmp_path: Path,
    number_label: str,
    format_label: str,
    expected_number: str,
    expected_format: str,
):
    values = valid_form_values(tmp_path) | {
        "number_style": number_label,
        "output_format": format_label,
    }
    request = build_generation_request(values)
    assert request.export.number_style == expected_number
    assert request.export.output_format == expected_format


def test_membership_contact_details_are_complete():
    assert MEMBERSHIP_EMAIL == "kmrzm520@gmail.com"
    assert PROJECT_URL == "https://github.com/kmrzm521/morse-code-audio-generator"
    assert "GitHub 用户名" in MEMBERSHIP_GUIDE
    assert "本机机器码" in MEMBERSHIP_GUIDE
    assert MEMBERSHIP_EMAIL in MEMBERSHIP_GUIDE


def test_random_global_entity_uses_complete_rule_list(tmp_path: Path):
    values = valid_form_values(tmp_path) | {
        "mode": "global_callsign",
        "country": RANDOM_GLOBAL_ENTITY,
    }
    request = build_generation_request(values)
    assert request.text
    assert len(global_entity_names()) == 340
