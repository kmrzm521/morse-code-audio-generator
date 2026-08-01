import wave
from pathlib import Path

import pytest

from morse_app.core import build_timeline, iter_pcm_chunks, render_pcm, text_to_tokens
from morse_app.exporters import (
    ExportRequest,
    export_training_set,
    reserve_output_paths,
    write_lrc,
    write_mp3,
    write_mp3_chunks,
    write_wav,
    write_wav_chunks,
)


def test_wav_header_and_duration(tmp_path: Path):
    path = tmp_path / "tone.wav"
    events = build_timeline(text_to_tokens("PARIS"), 20)
    pcm = render_pcm(events, 700)
    write_wav(path, pcm)
    with wave.open(str(path), "rb") as stream:
        assert stream.getnchannels() == 1
        assert stream.getsampwidth() == 2
        assert stream.getframerate() == 44_100
        assert stream.getnframes() == len(pcm) // 2


def test_output_paths_do_not_overwrite_audio_or_lrc(tmp_path: Path):
    (tmp_path / "练习.mp3").write_bytes(b"old")
    paths = reserve_output_paths(tmp_path, "练习", ".mp3")
    assert paths.audio.name == "练习_2.mp3"
    assert paths.lrc.name == "练习_2.lrc"

    (tmp_path / "另一练习.lrc").write_text("old", encoding="utf-8")
    paths = reserve_output_paths(tmp_path, "另一练习", ".wav")
    assert paths.audio.name == "另一练习_2.wav"


def test_lrc_uses_timeline_start_times(tmp_path: Path):
    path = tmp_path / "timing.lrc"
    tokens = text_to_tokens("EE")
    timeline = build_timeline(tokens, 20)
    write_lrc(path, tokens, timeline, {"wpm": 20})
    text = path.read_text(encoding="utf-8")
    assert "[00:00.000] E (.)" in text
    assert "[00:00.240] E (.)" in text
    assert "摩斯电码练习" in text
    assert "每分钟 20 字" in text
    assert "Morse Code Practice" not in text
    assert "WPM" not in text


def test_pcm_chunks_match_single_render():
    timeline = build_timeline(text_to_tokens("PARIS PARIS"), 20)
    expected = render_pcm(timeline, 700)
    chunks = list(iter_pcm_chunks(timeline, 700, chunk_seconds=1))
    assert b"".join(chunks) == expected
    assert max(map(len, chunks)) <= 44_100 * 2


def test_chunk_writers_create_audio(tmp_path: Path):
    timeline = build_timeline(text_to_tokens("TEST"), 20)
    wav_path = tmp_path / "分块.wav"
    mp3_path = tmp_path / "分块.mp3"
    write_wav_chunks(wav_path, iter_pcm_chunks(timeline, 700, chunk_seconds=1))
    write_mp3_chunks(mp3_path, iter_pcm_chunks(timeline, 700, chunk_seconds=1))
    assert wav_path.stat().st_size > 44
    assert mp3_path.stat().st_size > 100


def test_mp3_encoder_writes_mpeg_data(tmp_path: Path):
    pytest.importorskip("lameenc")
    path = tmp_path / "tone.mp3"
    pcm = render_pcm(build_timeline(text_to_tokens("TEST"), 20), 700)
    write_mp3(path, pcm)
    data = path.read_bytes()
    assert len(data) > 100
    assert data.startswith(b"ID3") or data[0] == 0xFF


def test_export_training_set_creates_audio_and_lrc(tmp_path: Path):
    result = export_training_set(
        ExportRequest(
            text="CQ TEST",
            output_dir=tmp_path,
            stem="字母_每分钟20字_700赫兹",
            output_format="wav",
            character_wpm=20,
            effective_wpm=None,
            frequency_hz=700,
            number_style="long",
            simulated_callsign=False,
        )
    )
    assert result.audio_path.exists()
    assert result.lrc_path.exists()
    assert result.duration_seconds > 0


def test_export_rejects_invalid_format(tmp_path: Path):
    request = ExportRequest(
        text="TEST",
        output_dir=tmp_path,
        stem="test",
        output_format="flac",
        character_wpm=20,
        effective_wpm=None,
        frequency_hz=700,
        number_style="long",
        simulated_callsign=False,
    )
    with pytest.raises(ValueError, match="波形音频.*压缩音频"):
        export_training_set(request)
