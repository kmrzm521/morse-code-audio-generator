from dataclasses import replace
from pathlib import Path

import pytest

from morse_app.settings import (
    AppSettings,
    load_settings,
    save_settings,
    validate_settings,
)


def test_defaults_match_product_design():
    settings = AppSettings()
    assert settings.output_format == "mp3"
    assert settings.character_wpm == 15
    assert settings.frequency_hz == 700
    assert settings.farnsworth_enabled is False


def test_corrupt_config_falls_back_to_defaults(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text("not json", encoding="utf-8")
    assert load_settings(path) == AppSettings()


def test_unknown_config_keys_are_ignored(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text('{"character_wpm": 18, "future_key": true}', encoding="utf-8")
    assert load_settings(path).character_wpm == 18


def test_save_and_load_round_trip(tmp_path: Path):
    path = tmp_path / "settings.json"
    expected = replace(AppSettings(), character_wpm=22, output_format="wav")
    save_settings(expected, path)
    assert load_settings(path) == expected


@pytest.mark.parametrize("frequency", [299, 1201])
def test_rejects_frequency_outside_range(frequency):
    with pytest.raises(ValueError, match="300.*1200"):
        validate_settings(replace(AppSettings(), frequency_hz=frequency))


def test_rejects_farnsworth_speed_not_lower_than_character_speed():
    settings = replace(
        AppSettings(),
        farnsworth_enabled=True,
        character_wpm=15,
        effective_wpm=15,
    )
    with pytest.raises(ValueError, match="有效速度"):
        validate_settings(settings)


def test_invalid_values_in_config_fall_back_to_defaults(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text('{"frequency_hz": 5000}', encoding="utf-8")
    assert load_settings(path) == AppSettings()
