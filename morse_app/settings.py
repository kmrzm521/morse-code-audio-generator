"""本地 JSON 设置。"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppSettings:
    mode: str = "letters"
    group_size: int = 5
    duration_seconds: int = 60
    character_wpm: int = 15
    farnsworth_enabled: bool = False
    effective_wpm: int = 10
    frequency_hz: int = 700
    number_style: str = "long"
    output_format: str = "mp3"
    output_dir: str = ""
    province: str = "北京"
    country: str = "中国"
    station_type: str = "G"
    callsign_file: str = ""


def default_settings_path() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home()))
    return base / "MorseGenerator" / "settings.json"


def validate_settings(settings: AppSettings) -> None:
    valid_modes = {
        "letters", "numbers", "mixed", "punctuation", "prosigns", "q_codes",
        "chinese_callsign", "global_callsign", "local_callsigns", "custom",
    }
    if settings.mode not in valid_modes:
        raise ValueError("内容类型无效")
    if not 1 <= settings.group_size <= 20:
        raise ValueError("每组字符数必须在 1 至 20 之间")
    if not 5 <= settings.duration_seconds <= 3600:
        raise ValueError("生成时长必须在 5 至 3600 秒之间")
    if not 5 <= settings.character_wpm <= 60:
        raise ValueError("字符速度必须在 5 至 60 WPM 之间")
    if not 300 <= settings.frequency_hz <= 1200:
        raise ValueError("音调频率必须在 300 至 1200 Hz 之间")
    if settings.farnsworth_enabled and not 1 <= settings.effective_wpm < settings.character_wpm:
        raise ValueError("Farnsworth 有效速度必须低于字符速度且至少为 1 WPM")
    if settings.number_style not in {"long", "short"}:
        raise ValueError("数字编码必须是 long 或 short")
    if settings.output_format not in {"wav", "mp3"}:
        raise ValueError("输出格式只能是 WAV 或 MP3")


def load_settings(path: Path | None = None) -> AppSettings:
    target = Path(path) if path is not None else default_settings_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return AppSettings()
        allowed = {field.name for field in fields(AppSettings)}
        settings = AppSettings(**{key: value for key, value in data.items() if key in allowed})
        validate_settings(settings)
        return settings
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return AppSettings()


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    validate_settings(settings)
    target = Path(path) if path is not None else default_settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(asdict(settings), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
