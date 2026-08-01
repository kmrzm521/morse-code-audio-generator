"""WAV、MP3 和同步 LRC 文件导出。"""

from __future__ import annotations

import os
import re
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from .core import MorseToken, TimingEvent, build_timeline, iter_pcm_chunks, text_to_tokens


@dataclass(frozen=True, slots=True)
class OutputPaths:
    audio: Path
    lrc: Path


@dataclass(frozen=True, slots=True)
class ExportRequest:
    text: str
    output_dir: Path
    stem: str
    output_format: str
    character_wpm: float
    effective_wpm: float | None
    frequency_hz: float
    number_style: str
    simulated_callsign: bool


@dataclass(frozen=True, slots=True)
class ExportResult:
    audio_path: Path
    lrc_path: Path
    duration_seconds: float
    text: str


def _safe_stem(stem: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", stem).strip(" .")
    return safe or "摩斯练习"


def reserve_output_paths(directory: Path, stem: str, extension: str) -> OutputPaths:
    directory = Path(directory)
    extension = extension.lower()
    if extension not in {".wav", ".mp3"}:
        raise ValueError("输出格式只能选择波形音频或压缩音频")
    base = _safe_stem(stem)
    sequence = 1
    while True:
        suffix = "" if sequence == 1 else f"_{sequence}"
        audio = directory / f"{base}{suffix}{extension}"
        lrc = directory / f"{base}{suffix}.lrc"
        if not audio.exists() and not lrc.exists():
            return OutputPaths(audio, lrc)
        sequence += 1


def _temporary_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")


def write_wav(path: Path, pcm: bytes, sample_rate: int = 44_100) -> None:
    write_wav_chunks(path, (pcm,), sample_rate)


def write_wav_chunks(
    path: Path,
    chunks: Iterable[bytes],
    sample_rate: int = 44_100,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(path)
    try:
        with wave.open(str(temporary), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(sample_rate)
            for chunk in chunks:
                stream.writeframesraw(chunk)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_mp3(
    path: Path,
    pcm: bytes,
    sample_rate: int = 44_100,
    bitrate_kbps: int = 128,
) -> None:
    write_mp3_chunks(path, (pcm,), sample_rate, bitrate_kbps)


def write_mp3_chunks(
    path: Path,
    chunks: Iterable[bytes],
    sample_rate: int = 44_100,
    bitrate_kbps: int = 128,
) -> None:
    try:
        import lameenc
    except ImportError as error:
        raise RuntimeError("缺少压缩音频编码器，仍可选择波形音频") from error

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(bitrate_kbps)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(1)
    encoder.set_quality(2)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(path)
    try:
        written = 0
        with temporary.open("wb") as stream:
            for chunk in chunks:
                encoded = encoder.encode(chunk)
                stream.write(encoded)
                written += len(encoded)
            final = encoder.flush()
            stream.write(final)
            written += len(final)
        if not written:
            raise RuntimeError("压缩音频编码没有产生数据")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _lrc_timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return f"{minutes:02d}:{remainder:06.3f}"


def write_lrc(
    path: Path,
    tokens: list[MorseToken],
    timeline: list[TimingEvent],
    metadata: Mapping[str, object],
) -> None:
    starts: dict[int, float] = {}
    for event in timeline:
        if event.kind == "tone" and event.token_index is not None:
            starts.setdefault(event.token_index, event.start)

    lines = [
        f"[ti:{metadata.get('title', '摩斯电码练习')}]",
        "[ar:BG2GNR]",
        "[by:离线摩斯电码生成器]",
        f"[speed:每分钟 {metadata.get('wpm', '')} 字]",
    ]
    if metadata.get("simulated_callsign"):
        lines.append("[re:标准模拟呼号，不代表真实签发]")
    for token_index, token in enumerate(tokens):
        if token.text == " " or token_index not in starts:
            continue
        lines.append(f"[{_lrc_timestamp(starts[token_index])}] {token.text} ({token.code})")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(path)
    try:
        temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def export_training_set(request: ExportRequest) -> ExportResult:
    output_format = request.output_format.lower()
    if output_format not in {"wav", "mp3"}:
        raise ValueError("输出格式只能选择波形音频或压缩音频")
    if not request.text.strip():
        raise ValueError("生成内容不能为空")

    tokens = text_to_tokens(request.text, request.number_style)
    timeline = build_timeline(tokens, request.character_wpm, request.effective_wpm)
    duration = timeline[-1].start + timeline[-1].duration if timeline else 0.0
    paths = reserve_output_paths(request.output_dir, request.stem, f".{output_format}")

    try:
        if output_format == "wav":
            write_wav_chunks(paths.audio, iter_pcm_chunks(timeline, request.frequency_hz))
        else:
            try:
                write_mp3_chunks(paths.audio, iter_pcm_chunks(timeline, request.frequency_hz))
            except Exception as error:
                recovery = reserve_output_paths(request.output_dir, f"{request.stem}_恢复", ".wav")
                write_wav_chunks(
                    recovery.audio,
                    iter_pcm_chunks(timeline, request.frequency_hz),
                )
                raise RuntimeError(
                    f"压缩音频生成失败，已保留波形音频：{recovery.audio}"
                ) from error
        write_lrc(
            paths.lrc,
            tokens,
            timeline,
            {
                "title": request.stem,
                "wpm": request.character_wpm,
                "simulated_callsign": request.simulated_callsign,
            },
        )
    except Exception:
        paths.audio.unlink(missing_ok=True)
        paths.lrc.unlink(missing_ok=True)
        raise

    return ExportResult(paths.audio, paths.lrc, duration, request.text)
