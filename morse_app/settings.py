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


def validate_settings(settings: AppSettings, *, is_member: bool = False) -> None:
    valid_modes = {
        "letters", "numbers", "mixed", "punctuation", "prosigns", "q_codes",
        "chinese_callsign", "global_callsign", "custom",
    }
    if settings.mode not in valid_modes:
        raise ValueError("内容类型无效")
    if not 1 <= settings.group_size <= 20:
        raise ValueError("每组字符数必须在 1 至 20 之间")
    if settings.duration_seconds < 5:
        raise ValueError("生成时长不能少于 5 秒")
    if not is_member and settings.duration_seconds > 300:
        raise ValueError("普通用户每次最多生成 5 分钟，超过后需要永久会员")
    if not 5 <= settings.character_wpm <= 60:
        raise ValueError("字符速度必须在每分钟 5 至 60 字之间")
    if not 300 <= settings.frequency_hz <= 1200:
        raise ValueError("音调频率必须在 300 至 1200 赫兹之间")
    if settings.farnsworth_enabled and not 1 <= settings.effective_wpm < settings.character_wpm:
        raise ValueError("间隔降速必须低于字符速度且至少为每分钟 1 字")
    if settings.number_style not in {"long", "short"}:
        raise ValueError("数字编码必须选择普通数字或缩短数字")
    if settings.output_format not in {"wav", "mp3"}:
        raise ValueError("输出格式只能选择波形音频或压缩音频")


def load_settings(path: Path | None = None) -> AppSettings:
    target = Path(path) if path is not None else default_settings_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return AppSettings()
        allowed = {field.name for field in fields(AppSettings)}
        settings = AppSettings(**{key: value for key, value in data.items() if key in allowed})
        validate_settings(settings, is_member=True)
        return settings
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return AppSettings()


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    validate_settings(settings, is_member=True)
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
