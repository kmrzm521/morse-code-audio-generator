from pathlib import Path

import pytest

from morse_app.gui import build_generation_request


def valid_form_values(tmp_path: Path) -> dict[str, object]:
    return {
        "mode": "letters",
        "group_size": "5",
        "duration_seconds": "5",
        "character_wpm": "15",
        "farnsworth_enabled": False,
        "effective_wpm": "10",
        "frequency_hz": "700",
        "number_style": "long",
        "output_format": "mp3",
        "output_dir": str(tmp_path),
        "province": "北京",
        "country": "中国",
        "station_type": "G",
        "callsign_file": "",
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


def test_local_callsign_mode_requires_existing_file(tmp_path: Path):
    values = valid_form_values(tmp_path) | {
        "mode": "local_callsigns",
        "callsign_file": str(tmp_path / "missing.txt"),
    }
    with pytest.raises(ValueError, match="呼号表"):
        build_generation_request(values)


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
