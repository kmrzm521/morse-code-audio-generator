# Offline Morse Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small Windows Python GUI that generates standards-based Morse WAV or MP3 audio and synchronized LRC files entirely offline.

**Architecture:** Keep Morse timing and PCM generation as pure, testable standard-library modules. Isolate callsign/content rules, file exporters, settings, and Tkinter orchestration so the GUI never owns business logic. Use `lameenc` as the only runtime dependency and write files atomically from a background worker.

**Tech Stack:** Python 3.13, Tkinter, standard library, lameenc 1.8.4, pytest, PyInstaller.

## Global Constraints

- Runtime must be fully offline and must never download data or open network connections.
- Default output is MP3; WAV remains available; MP4 is excluded.
- Morse symbols and 1:3:7 spacing follow ITU-R M.1677-1.
- Default character speed is 15 WPM and default tone is 700 Hz; tone range is 300-1200 Hz.
- Audio is 44.1 kHz, 16-bit, mono PCM before export.
- MP3 uses `lameenc`; FFmpeg, NumPy, SciPy, OpenCV, pygame, transformers, and Edge TTS are excluded.
- Generated callsigns must be labeled as simulated; real callsigns come only from user-imported local TXT/CSV files.
- No output file may silently overwrite an existing file.
- All user-visible text and errors are Chinese.

---

### Task 1: Project skeleton and Morse conversion

**Files:**
- Create: `morse_app/__init__.py`
- Create: `morse_app/core.py`
- Create: `tests/test_core.py`
- Create: `pyproject.toml`
- Create: `requirements.txt`

**Interfaces:**
- Produces: `text_to_tokens(text: str, number_style: str = "long") -> list[MorseToken]`
- Produces: `MorseToken(text: str, code: str)` immutable dataclass.

- [ ] **Step 1: Write failing conversion tests**

```python
from morse_app.core import MorseToken, text_to_tokens


def test_converts_letters_digits_and_punctuation():
    assert text_to_tokens("CQ 5?") == [
        MorseToken("C", "-.-."), MorseToken("Q", "--.-"),
        MorseToken(" ", "/"), MorseToken("5", "....."),
        MorseToken("?", "..--.."),
    ]


def test_short_digit_style_uses_cut_numbers():
    assert [t.code for t in text_to_tokens("0123456789", "short")] == [
        "-", ".-", "..-", "...-", "....-",
        ".....", "-....", "-...", "-..", "-.",
    ]


def test_prosign_is_one_morse_character():
    assert text_to_tokens("<AR>") == [MorseToken("AR", ".-.-.")]


def test_rejects_unknown_character():
    import pytest
    with pytest.raises(ValueError, match="不支持的字符"):
        text_to_tokens("你好")
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m pytest tests/test_core.py -v`
Expected: FAIL because `morse_app.core` does not exist.

- [ ] **Step 3: Implement the table and conversion**

```python
@dataclass(frozen=True, slots=True)
class MorseToken:
    text: str
    code: str


def text_to_tokens(text: str, number_style: str = "long") -> list[MorseToken]:
    if number_style not in {"long", "short"}:
        raise ValueError("数字编码必须是 long 或 short")
    # Normalize ASCII case, preserve spaces as group separators, and fail on
    # unsupported characters instead of silently deleting training content.
```

Include A-Z, 0-9, `. , ? ! / = + ( )`. Parse `<AR>`, `<SK>`, and `<BT>` as explicit single prosign tokens so their letters are not separated as ordinary characters; the UI displays them without angle brackets.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_core.py -v`
Expected: all Task 1 tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add morse_app tests pyproject.toml requirements.txt
git commit -m "feat: add Morse conversion core"
```

### Task 2: Standards-based timing, Farnsworth, and PCM

**Files:**
- Modify: `morse_app/core.py`
- Modify: `tests/test_core.py`

**Interfaces:**
- Consumes: `MorseToken` and `text_to_tokens` from Task 1.
- Produces: `TimingEvent(kind: Literal["tone", "silence"], start: float, duration: float, token_index: int | None)`.
- Produces: `build_timeline(tokens, character_wpm, effective_wpm=None) -> list[TimingEvent]`.
- Produces: `render_pcm(events, frequency, sample_rate=44100, amplitude=0.8) -> bytes`.

- [ ] **Step 1: Write failing timing tests**

```python
def test_standard_timing_uses_one_three_seven_units():
    tokens = text_to_tokens("EE E")
    events = build_timeline(tokens, character_wpm=20)
    assert events[0].duration == pytest.approx(0.06)  # one dit
    assert any(e.kind == "silence" and e.duration == pytest.approx(0.18) for e in events)
    assert any(e.kind == "silence" and e.duration == pytest.approx(0.42) for e in events)


def test_farnsworth_preserves_tones_and_expands_spacing():
    normal = build_timeline(text_to_tokens("PARIS PARIS"), 20)
    slow = build_timeline(text_to_tokens("PARIS PARIS"), 20, effective_wpm=10)
    assert [e.duration for e in normal if e.kind == "tone"] == pytest.approx(
        [e.duration for e in slow if e.kind == "tone"]
    )
    assert sum(e.duration for e in slow) > sum(e.duration for e in normal)


def test_pcm_has_expected_shape_and_faded_edges():
    pcm = render_pcm(build_timeline(text_to_tokens("E"), 20), 700)
    samples = array("h"); samples.frombytes(pcm)
    assert len(samples) == round(44100 * 0.06)
    assert samples[0] == 0
    assert abs(samples[-1]) < 500
    assert max(abs(v) for v in samples) <= 32767
```

- [ ] **Step 2: Run and verify RED**

Run: `python -m pytest tests/test_core.py -v`
Expected: FAIL because timeline and PCM APIs are missing.

- [ ] **Step 3: Implement timing and rendering**

Use `dit = 1.2 / character_wpm`. Build tone/silence events without cumulative rounding; convert absolute event boundaries to sample indexes. Apply a 5 ms raised-cosine fade capped at half the tone duration. Farnsworth derives expanded character/word gaps from the difference between target PARIS duration at character speed and effective speed; reject effective speed greater than or equal to character speed.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_core.py -v`
Expected: all core tests PASS without warnings.

- [ ] **Step 5: Commit**

```powershell
git add morse_app/core.py tests/test_core.py
git commit -m "feat: generate standards-based Morse PCM"
```

### Task 3: Random content and standards-based callsigns

**Files:**
- Create: `morse_app/content.py`
- Create: `morse_app/callsigns.py`
- Create: `tests/test_content.py`
- Create: `tests/test_callsigns.py`

**Interfaces:**
- Produces: `generate_group(mode: str, group_size: int, rng: random.Random) -> str`.
- Produces: `generate_until_duration(mode, group_size, target_seconds, timing_options, rng) -> str`.
- Produces: `generate_chinese_callsign(province: str, station_type: str, rng) -> str`.
- Produces: `generate_global_callsign(country: str, rng) -> str` for eight named countries.
- Produces: `is_plausible_callsign(value: str) -> bool`.

- [ ] **Step 1: Write failing content and callsign tests**

```python
def test_seeded_content_is_repeatable():
    assert generate_group("letters", 5, random.Random(7)) == generate_group(
        "letters", 5, random.Random(7)
    )


@pytest.mark.parametrize("province,digit", [("北京", "1"), ("广东", "7"), ("新疆", "0")])
def test_chinese_callsign_uses_official_district(province, digit):
    call = generate_chinese_callsign(province, "G", random.Random(3))
    assert call.startswith(f"BG{digit}")
    assert is_plausible_callsign(call)


def test_chinese_suffix_excludes_reserved_groups():
    for seed in range(500):
        suffix = generate_chinese_callsign("北京", "G", random.Random(seed))[3:]
        assert suffix not in {"SOS", "XXX", "TTT"}
        assert not (len(suffix) == 3 and "QOA" <= suffix <= "QUZ")


@pytest.mark.parametrize("country", ["中国", "美国", "日本", "德国", "俄罗斯", "英国", "加拿大", "澳大利亚"])
def test_global_generator_returns_plausible_callsign(country):
    assert is_plausible_callsign(generate_global_callsign(country, random.Random(11)))
```

- [ ] **Step 2: Run and verify RED**

Run: `python -m pytest tests/test_content.py tests/test_callsigns.py -v`
Expected: FAIL because content and callsign modules are missing.

- [ ] **Step 3: Implement minimal generators**

Encode the MIIT province/district/suffix ranges as immutable data and document the source date beside the table. Encode explicit patterns for the eight supported countries; do not create a generic “prefix + random text” fallback. `generate_until_duration` appends complete groups until the timeline first reaches or exceeds the requested duration.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_content.py tests/test_callsigns.py -v`
Expected: all Task 3 tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add morse_app/content.py morse_app/callsigns.py tests/test_content.py tests/test_callsigns.py
git commit -m "feat: add offline training content and callsigns"
```

### Task 4: Local real-callsign import

**Files:**
- Modify: `morse_app/callsigns.py`
- Modify: `tests/test_callsigns.py`

**Interfaces:**
- Produces: `load_callsigns(path: Path) -> list[str]` supporting TXT and CSV.

- [ ] **Step 1: Write failing import tests**

```python
def test_loads_deduplicated_txt_callsigns(tmp_path):
    path = tmp_path / "calls.txt"
    path.write_text("bg2gnr\n BG2GNR \ninvalid value\nK1ABC\n", encoding="utf-8")
    assert load_callsigns(path) == ["BG2GNR", "K1ABC"]


def test_loads_named_csv_column(tmp_path):
    path = tmp_path / "calls.csv"
    path.write_text("name,callsign\nA,JA1ABC\nB,DL1XYZ\n", encoding="utf-8-sig")
    assert load_callsigns(path) == ["JA1ABC", "DL1XYZ"]


def test_rejects_csv_without_callsign_column(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("name,city\nA,B\n", encoding="utf-8")
    with pytest.raises(ValueError, match="呼号列"):
        load_callsigns(path)
```

- [ ] **Step 2: Run and verify RED**

Run: `python -m pytest tests/test_callsigns.py -v`
Expected: FAIL because `load_callsigns` is missing.

- [ ] **Step 3: Implement local import**

Use `csv.DictReader` with UTF-8 BOM support; accept headers case-insensitively from `callsign`, `call`, and `呼号`. Preserve first-seen order, discard invalid rows, reject unsupported extensions and return an error when no usable callsigns remain.

- [ ] **Step 4: Verify GREEN and commit**

Run: `python -m pytest tests/test_callsigns.py -v`
Expected: all callsign tests PASS.

```powershell
git add morse_app/callsigns.py tests/test_callsigns.py
git commit -m "feat: import local callsign lists"
```

### Task 5: Atomic WAV, MP3, and LRC export

**Files:**
- Create: `morse_app/exporters.py`
- Create: `tests/test_exporters.py`

**Interfaces:**
- Produces: `reserve_output_paths(directory, stem, extension) -> OutputPaths`.
- Produces: `write_wav(path, pcm, sample_rate=44100) -> None`.
- Produces: `write_mp3(path, pcm, sample_rate=44100, bitrate_kbps=128) -> None`.
- Produces: `write_lrc(path, tokens, timeline, metadata) -> None`.
- Produces: `export_training_set(request: ExportRequest) -> ExportResult`.

- [ ] **Step 1: Write failing exporter tests**

```python
def test_wav_header_and_duration(tmp_path):
    path = tmp_path / "tone.wav"
    pcm = render_pcm(build_timeline(text_to_tokens("PARIS"), 20), 700)
    write_wav(path, pcm)
    with wave.open(str(path), "rb") as stream:
        assert stream.getnchannels() == 1
        assert stream.getsampwidth() == 2
        assert stream.getframerate() == 44100


def test_output_paths_do_not_overwrite(tmp_path):
    (tmp_path / "练习.mp3").write_bytes(b"old")
    paths = reserve_output_paths(tmp_path, "练习", ".mp3")
    assert paths.audio.name == "练习_2.mp3"


def test_lrc_uses_timeline_start_times(tmp_path):
    path = tmp_path / "timing.lrc"
    tokens = text_to_tokens("EE")
    timeline = build_timeline(tokens, 20)
    write_lrc(path, tokens, timeline, {"title": "测试", "wpm": 20})
    text = path.read_text(encoding="utf-8")
    assert "[00:00.000] E (.)" in text
    assert "[00:00.240] E (.)" in text
```

Add an MP3 test guarded with `pytest.importorskip("lameenc")`; assert the file starts with an ID3 header or a valid MPEG frame sync and has nontrivial length.

- [ ] **Step 2: Run and verify RED**

Run: `python -m pytest tests/test_exporters.py -v`
Expected: FAIL because exporter APIs are missing.

- [ ] **Step 3: Implement atomic exporters**

Write `.tmp` files in the destination directory, flush and close them, then use `Path.replace` only after success. For MP3, configure `lameenc.Encoder` for one channel, 44.1 kHz, 128 kbps, encode PCM bytes, and append `flush()`. On MP3 failure, rename the valid temporary WAV to a recovery filename and include it in the raised Chinese error.

- [ ] **Step 4: Verify GREEN and commit**

Run: `python -m pytest tests/test_exporters.py -v`
Expected: exporter tests PASS; MP3 test is PASS when lameenc is installed or SKIPPED with an explicit reason.

```powershell
git add morse_app/exporters.py tests/test_exporters.py
git commit -m "feat: export WAV MP3 and synchronized LRC"
```

### Task 6: Validated local settings

**Files:**
- Create: `morse_app/settings.py`
- Create: `tests/test_settings.py`

**Interfaces:**
- Produces: `AppSettings` dataclass with defaults.
- Produces: `load_settings(path: Path | None = None) -> AppSettings`.
- Produces: `save_settings(settings, path: Path | None = None) -> None`.
- Produces: `validate_settings(settings) -> None`.

- [ ] **Step 1: Write failing settings tests**

```python
def test_defaults_match_product_design():
    settings = AppSettings()
    assert settings.output_format == "mp3"
    assert settings.character_wpm == 15
    assert settings.frequency_hz == 700


def test_corrupt_config_falls_back_to_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not json", encoding="utf-8")
    assert load_settings(path) == AppSettings()


@pytest.mark.parametrize("frequency", [299, 1201])
def test_rejects_frequency_outside_range(frequency):
    with pytest.raises(ValueError, match="300.*1200"):
        validate_settings(replace(AppSettings(), frequency_hz=frequency))
```

- [ ] **Step 2: Run and verify RED**

Run: `python -m pytest tests/test_settings.py -v`
Expected: FAIL because settings APIs are missing.

- [ ] **Step 3: Implement settings**

Default path is `%APPDATA%/MorseGenerator/settings.json`; use a local temp file and replace for atomic saves. Ignore unknown JSON keys for forward compatibility, replace missing keys with defaults, and validate all numeric bounds and Farnsworth relationships.

- [ ] **Step 4: Verify GREEN and commit**

Run: `python -m pytest tests/test_settings.py -v`
Expected: all settings tests PASS.

```powershell
git add morse_app/settings.py tests/test_settings.py
git commit -m "feat: persist validated local settings"
```

### Task 7: Tkinter GUI and background generation

**Files:**
- Create: `morse_app/gui.py`
- Create: `main.py`
- Create: `tests/test_gui_logic.py`

**Interfaces:**
- Produces: `GenerationRequest` and `build_generation_request(form_values) -> GenerationRequest` as GUI-independent validation.
- Produces: `MorseGeneratorApp(root: tk.Tk)`.

- [ ] **Step 1: Write failing GUI-logic tests**

```python
def test_custom_mode_requires_text(tmp_path):
    values = valid_form_values(tmp_path) | {"mode": "custom", "custom_text": " "}
    with pytest.raises(ValueError, match="自定义文本不能为空"):
        build_generation_request(values)


def test_simulated_callsign_is_labeled(tmp_path):
    request = build_generation_request(
        valid_form_values(tmp_path) | {"mode": "chinese_callsign"}
    )
    assert request.simulated_callsign is True
```

- [ ] **Step 2: Run and verify RED**

Run: `python -m pytest tests/test_gui_logic.py -v`
Expected: FAIL because GUI logic is missing.

- [ ] **Step 3: Implement the GUI**

Build a single resizable Tkinter window with grouped sections for content, timing, output, preview, progress, and status. Enable only controls relevant to the selected mode. Run `export_training_set` in `ThreadPoolExecutor(max_workers=1)`; publish progress/results with `root.after`, never update widgets from the worker. “打开文件夹” uses `os.startfile` only after a successful result and direct user click.

- [ ] **Step 4: Verify logic and manually launch**

Run: `python -m pytest tests/test_gui_logic.py -v`
Expected: all GUI-logic tests PASS.

Run: `python main.py`
Expected: window opens, mode controls toggle correctly, and closing the window terminates the executor cleanly.

- [ ] **Step 5: Commit**

```powershell
git add morse_app/gui.py main.py tests/test_gui_logic.py
git commit -m "feat: add offline Tkinter application"
```

### Task 8: Documentation, packaging, and final verification

**Files:**
- Create: `README.md`
- Create: `build.ps1`
- Create: `morse-generator.spec`
- Create: `.gitignore`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: all prior modules and the `main.py` entry point.
- Produces: reproducible source setup and `dist/摩斯电码生成器.exe` build.

- [ ] **Step 1: Add packaging smoke test**

Add `tests/test_package.py`:

```python
def test_imports_without_optional_gui_side_effects():
    import morse_app.core
    import morse_app.content
    import morse_app.callsigns
    import morse_app.exporters
    import morse_app.settings
```

- [ ] **Step 2: Run full tests before documentation**

Run: `python -m pytest -q`
Expected: all tests PASS; no unexpected warnings.

- [ ] **Step 3: Write user and build documentation**

Document Python 3.13 setup, `pip install -r requirements.txt`, `python main.py`, TXT/CSV callsign format, simulated-callsign warning, WAV/MP3 behavior, Farnsworth meaning, offline guarantee, and the PyInstaller build command. Pin `lameenc==1.8.4` and `PyInstaller==6.11.1` in build dependencies.

- [ ] **Step 4: Build and inspect executable**

Run: `powershell -ExecutionPolicy Bypass -File .\build.ps1`
Expected: `dist/摩斯电码生成器.exe` exists and is substantially smaller than the 352,428,014-byte v5.0 executable.

- [ ] **Step 5: Final automated and manual verification**

Run: `python -m pytest -q`
Expected: all tests PASS.

Manual checklist:

- Disconnect network or block the app, then generate MP3 and WAV.
- Play both outputs and verify clean tone edges.
- Verify LRC timestamps follow the audio.
- Generate every content mode and all eight country rules.
- Import representative UTF-8 TXT and CSV callsign lists.
- Verify invalid inputs show Chinese messages and leave no final partial file.
- Verify a second generation does not overwrite the first.
- Verify GUI remains responsive during a long generation.

- [ ] **Step 6: Commit**

```powershell
git add README.md build.ps1 morse-generator.spec .gitignore pyproject.toml tests/test_package.py
git commit -m "build: document and package offline Morse generator"
```
