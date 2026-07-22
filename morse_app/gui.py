"""Tkinter 图形界面及与界面无关的表单校验。"""

from __future__ import annotations

import os
import random
import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Mapping

from .callsigns import (
    CHINA_PROVINCE_RANGES,
    generate_chinese_callsign,
    generate_global_callsign,
    load_callsigns,
)
from .content import generate_until_duration
from .core import build_timeline, text_to_tokens
from .exporters import ExportRequest, ExportResult, export_training_set
from .settings import AppSettings, load_settings, save_settings, validate_settings


MODE_LABELS = {
    "随机字母": "letters",
    "随机数字": "numbers",
    "字母数字混合": "mixed",
    "标点符号": "punctuation",
    "通联符号": "prosigns",
    "Q 简语": "q_codes",
    "中国模拟呼号": "chinese_callsign",
    "全球模拟呼号": "global_callsign",
    "本地真实呼号表": "local_callsigns",
    "自定义文本": "custom",
}
MODE_NAMES = {value: key for key, value in MODE_LABELS.items()}
COUNTRIES = ("中国", "美国", "日本", "德国", "俄罗斯", "英国", "加拿大", "澳大利亚")


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    text: str
    export: ExportRequest


def _number(values: Mapping[str, object], name: str, display: str, cast):
    try:
        return cast(values[name])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{display}必须是数字") from error


def _duration(text: str, wpm: int, effective_wpm: int | None, number_style: str) -> float:
    events = build_timeline(text_to_tokens(text, number_style), wpm, effective_wpm)
    return events[-1].start + events[-1].duration if events else 0.0


def _repeat_callsigns(
    factory,
    target_seconds: int,
    wpm: int,
    effective_wpm: int | None,
    number_style: str,
) -> str:
    calls: list[str] = []
    while True:
        calls.append(factory())
        text = " ".join(calls)
        if _duration(text, wpm, effective_wpm, number_style) >= target_seconds:
            return text


def build_generation_request(
    values: Mapping[str, object],
    rng: random.Random | None = None,
) -> GenerationRequest:
    """校验表单并一次性确定本次生成内容。"""
    rng = rng or random.Random()
    mode = str(values.get("mode", ""))
    group_size = _number(values, "group_size", "每组字符数", int)
    duration_seconds = _number(values, "duration_seconds", "生成时长", int)
    character_wpm = _number(values, "character_wpm", "字符速度", int)
    effective_value = _number(values, "effective_wpm", "有效速度", int)
    frequency_hz = _number(values, "frequency_hz", "音调频率", int)
    farnsworth_enabled = bool(values.get("farnsworth_enabled", False))
    effective_wpm = effective_value if farnsworth_enabled else None
    number_style = str(values.get("number_style", "long"))
    output_format = str(values.get("output_format", "mp3")).lower()
    output_dir_value = str(values.get("output_dir", "")).strip()
    if not output_dir_value:
        raise ValueError("请选择输出目录")
    output_dir = Path(output_dir_value)

    settings = AppSettings(
        mode=mode,
        group_size=group_size,
        duration_seconds=duration_seconds,
        character_wpm=character_wpm,
        farnsworth_enabled=farnsworth_enabled,
        effective_wpm=effective_value,
        frequency_hz=frequency_hz,
        number_style=number_style,
        output_format=output_format,
        output_dir=str(output_dir),
        province=str(values.get("province", "北京")),
        country=str(values.get("country", "中国")),
        station_type=str(values.get("station_type", "G")),
        callsign_file=str(values.get("callsign_file", "")),
    )
    validate_settings(settings)
    simulated = False
    if mode == "custom":
        text = str(values.get("custom_text", "")).strip().upper()
        if not text:
            raise ValueError("自定义文本不能为空")
    elif mode == "chinese_callsign":
        simulated = True
        text = _repeat_callsigns(
            lambda: generate_chinese_callsign(settings.province, settings.station_type, rng),
            duration_seconds, character_wpm, effective_wpm, number_style,
        )
    elif mode == "global_callsign":
        simulated = True
        text = _repeat_callsigns(
            lambda: generate_global_callsign(settings.country, rng),
            duration_seconds, character_wpm, effective_wpm, number_style,
        )
    elif mode == "local_callsigns":
        callsign_path = Path(settings.callsign_file)
        if not callsign_path.is_file():
            raise ValueError("请选择存在的本地呼号表")
        calls = load_callsigns(callsign_path)
        text = _repeat_callsigns(
            lambda: rng.choice(calls), duration_seconds, character_wpm,
            effective_wpm, number_style,
        )
    else:
        text = generate_until_duration(
            mode, group_size, duration_seconds,
            {
                "character_wpm": character_wpm,
                "effective_wpm": effective_wpm,
                "number_style": number_style,
            },
            rng,
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{MODE_NAMES[mode]}_{character_wpm}wpm_{frequency_hz}Hz_{timestamp}"
    export = ExportRequest(
        text=text,
        output_dir=output_dir,
        stem=stem,
        output_format=output_format,
        character_wpm=character_wpm,
        effective_wpm=effective_wpm,
        frequency_hz=frequency_hz,
        number_style=number_style,
        simulated_callsign=simulated,
    )
    return GenerationRequest(text, export)


class MorseGeneratorApp:
    """离线摩斯电码生成器主窗口。"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("摩斯电码生成器 v6.0（离线版）")
        self.root.geometry("820x760")
        self.root.minsize(760, 680)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="morse-export")
        self.future: Future[ExportResult] | None = None
        self.last_output_dir: Path | None = None
        self.settings = load_settings()
        self.variables: dict[str, tk.Variable] = {}
        self._build_ui()
        self._load_variables()
        self._update_control_states()
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _var(self, name: str, value, kind=tk.StringVar):
        variable = kind(value=value)
        self.variables[name] = variable
        return variable

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(outer, text="内容类型").grid(row=row, column=0, sticky="w", pady=4)
        self.mode_box = ttk.Combobox(
            outer, state="readonly", values=list(MODE_LABELS),
            textvariable=self._var("mode_label", "随机字母"),
        )
        self.mode_box.grid(row=row, column=1, sticky="ew", pady=4)
        self.mode_box.bind("<<ComboboxSelected>>", lambda _event: self._update_control_states())

        row += 1
        options = ttk.Frame(outer)
        options.grid(row=row, column=0, columnspan=2, sticky="ew")
        for column in range(6):
            options.columnconfigure(column, weight=1)
        ttk.Label(options, text="每组字符").grid(row=0, column=0)
        ttk.Spinbox(options, from_=1, to=20, width=7, textvariable=self._var("group_size", "5")).grid(row=0, column=1)
        ttk.Label(options, text="时长（秒）").grid(row=0, column=2)
        ttk.Spinbox(options, from_=5, to=3600, width=8, textvariable=self._var("duration_seconds", "60")).grid(row=0, column=3)
        ttk.Label(options, text="WPM").grid(row=0, column=4)
        ttk.Spinbox(options, from_=5, to=60, width=7, textvariable=self._var("character_wpm", "15")).grid(row=0, column=5)

        row += 1
        timing = ttk.Frame(outer)
        timing.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)
        self.farnsworth_check = ttk.Checkbutton(
            timing, text="Farnsworth", variable=self._var("farnsworth_enabled", False, tk.BooleanVar),
            command=self._update_control_states,
        )
        self.farnsworth_check.pack(side="left")
        ttk.Label(timing, text="有效 WPM").pack(side="left", padx=(12, 4))
        self.effective_spin = ttk.Spinbox(timing, from_=1, to=59, width=7, textvariable=self._var("effective_wpm", "10"))
        self.effective_spin.pack(side="left")
        ttk.Label(timing, text="音调 Hz").pack(side="left", padx=(20, 4))
        ttk.Spinbox(timing, from_=300, to=1200, width=8, textvariable=self._var("frequency_hz", "700")).pack(side="left")

        row += 1
        selectors = ttk.Frame(outer)
        selectors.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Label(selectors, text="数字编码").pack(side="left")
        ttk.Combobox(selectors, state="readonly", width=8, values=("long", "short"), textvariable=self._var("number_style", "long")).pack(side="left", padx=5)
        ttk.Label(selectors, text="格式").pack(side="left", padx=(20, 4))
        ttk.Combobox(selectors, state="readonly", width=7, values=("mp3", "wav"), textvariable=self._var("output_format", "mp3")).pack(side="left")

        row += 1
        self.callsign_frame = ttk.LabelFrame(outer, text="呼号设置", padding=8)
        self.callsign_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Label(self.callsign_frame, text="省份").grid(row=0, column=0)
        self.province_box = ttk.Combobox(self.callsign_frame, state="readonly", values=list(CHINA_PROVINCE_RANGES), textvariable=self._var("province", "北京"), width=12)
        self.province_box.grid(row=0, column=1, padx=5)
        ttk.Label(self.callsign_frame, text="台站字母").grid(row=0, column=2)
        self.station_box = ttk.Combobox(self.callsign_frame, state="readonly", values=tuple("GHIDABCEFKLR"), textvariable=self._var("station_type", "G"), width=6)
        self.station_box.grid(row=0, column=3, padx=5)
        ttk.Label(self.callsign_frame, text="国家").grid(row=0, column=4)
        self.country_box = ttk.Combobox(self.callsign_frame, state="readonly", values=COUNTRIES, textvariable=self._var("country", "中国"), width=10)
        self.country_box.grid(row=0, column=5, padx=5)
        self.callsign_entry = ttk.Entry(self.callsign_frame, textvariable=self._var("callsign_file", ""))
        self.callsign_entry.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(8, 0))
        self.callsign_frame.columnconfigure(4, weight=1)
        self.callsign_browse = ttk.Button(self.callsign_frame, text="选择呼号表", command=self._choose_callsign_file)
        self.callsign_browse.grid(row=1, column=5, pady=(8, 0))

        row += 1
        ttk.Label(outer, text="自定义文本").grid(row=row, column=0, sticky="nw", pady=4)
        self.custom_text = tk.Text(outer, height=4, wrap="word")
        self.custom_text.grid(row=row, column=1, sticky="nsew", pady=4)

        row += 1
        ttk.Label(outer, text="输出目录").grid(row=row, column=0, sticky="w", pady=4)
        output_frame = ttk.Frame(outer)
        output_frame.grid(row=row, column=1, sticky="ew")
        output_frame.columnconfigure(0, weight=1)
        ttk.Entry(output_frame, textvariable=self._var("output_dir", "")).grid(row=0, column=0, sticky="ew")
        ttk.Button(output_frame, text="浏览", command=self._choose_output_dir).grid(row=0, column=1, padx=(6, 0))

        row += 1
        ttk.Label(outer, text="本次内容预览").grid(row=row, column=0, sticky="nw", pady=4)
        self.preview = tk.Text(outer, height=9, wrap="word", state="disabled")
        self.preview.grid(row=row, column=1, sticky="nsew", pady=4)
        outer.rowconfigure(row, weight=1)

        row += 1
        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        row += 1
        self.status_var = tk.StringVar(value="就绪（完全离线）")
        ttk.Label(outer, textvariable=self.status_var).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1
        buttons = ttk.Frame(outer)
        buttons.grid(row=row, column=0, columnspan=2, pady=(10, 0))
        self.generate_button = ttk.Button(buttons, text="生成音频和 LRC", command=self._start_generation)
        self.generate_button.pack(side="left", padx=5)
        self.open_button = ttk.Button(buttons, text="打开输出文件夹", command=self._open_output, state="disabled")
        self.open_button.pack(side="left", padx=5)

    def _load_variables(self):
        values = asdict(self.settings)
        self.variables["mode_label"].set(MODE_NAMES.get(self.settings.mode, "随机字母"))
        for name, value in values.items():
            if name in self.variables:
                self.variables[name].set(value)
        if not self.variables["output_dir"].get():
            self.variables["output_dir"].set(str(Path.home() / "Documents"))

    def _mode(self) -> str:
        return MODE_LABELS[str(self.variables["mode_label"].get())]

    def _update_control_states(self):
        mode = self._mode()
        self.effective_spin.configure(state="normal" if self.variables["farnsworth_enabled"].get() else "disabled")
        self.custom_text.configure(state="normal" if mode == "custom" else "disabled")
        self.province_box.configure(state="readonly" if mode == "chinese_callsign" else "disabled")
        self.station_box.configure(state="readonly" if mode == "chinese_callsign" else "disabled")
        self.country_box.configure(state="readonly" if mode == "global_callsign" else "disabled")
        local_state = "normal" if mode == "local_callsigns" else "disabled"
        self.callsign_entry.configure(state=local_state)
        self.callsign_browse.configure(state=local_state)

    def _form_values(self) -> dict[str, object]:
        values = {name: variable.get() for name, variable in self.variables.items()}
        values["mode"] = self._mode()
        values["custom_text"] = self.custom_text.get("1.0", "end-1c")
        return values

    def _choose_output_dir(self):
        chosen = filedialog.askdirectory(title="选择输出目录")
        if chosen:
            self.variables["output_dir"].set(chosen)

    def _choose_callsign_file(self):
        chosen = filedialog.askopenfilename(
            title="选择本地呼号表",
            filetypes=(("呼号表", "*.txt *.csv"), ("所有文件", "*.*")),
        )
        if chosen:
            self.variables["callsign_file"].set(chosen)

    def _set_preview(self, text: str):
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    def _start_generation(self):
        try:
            request = build_generation_request(self._form_values())
            settings_values = self._form_values()
            save_settings(AppSettings(
                mode=self._mode(),
                group_size=int(settings_values["group_size"]),
                duration_seconds=int(settings_values["duration_seconds"]),
                character_wpm=int(settings_values["character_wpm"]),
                farnsworth_enabled=bool(settings_values["farnsworth_enabled"]),
                effective_wpm=int(settings_values["effective_wpm"]),
                frequency_hz=int(settings_values["frequency_hz"]),
                number_style=str(settings_values["number_style"]),
                output_format=str(settings_values["output_format"]),
                output_dir=str(settings_values["output_dir"]),
                province=str(settings_values["province"]),
                country=str(settings_values["country"]),
                station_type=str(settings_values["station_type"]),
                callsign_file=str(settings_values["callsign_file"]),
            ))
        except Exception as error:
            messagebox.showerror("参数错误", str(error), parent=self.root)
            return

        self._set_preview(request.text)
        self.generate_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.status_var.set("正在生成，请稍候……")
        self.progress.start(12)
        self.future = self.executor.submit(export_training_set, request.export)
        self.root.after(100, self._poll_generation)

    def _poll_generation(self):
        if self.future is None or not self.future.done():
            self.root.after(100, self._poll_generation)
            return
        self.progress.stop()
        self.generate_button.configure(state="normal")
        try:
            result = self.future.result()
        except Exception as error:
            self.status_var.set("生成失败")
            messagebox.showerror("生成失败", str(error), parent=self.root)
        else:
            self.last_output_dir = result.audio_path.parent
            self.open_button.configure(state="normal")
            self.status_var.set(
                f"已生成：{result.audio_path.name}（{result.duration_seconds:.1f} 秒）"
            )
            messagebox.showinfo(
                "生成成功",
                f"音频：{result.audio_path}\n歌词：{result.lrc_path}",
                parent=self.root,
            )
        finally:
            self.future = None

    def _open_output(self):
        if self.last_output_dir is not None and self.last_output_dir.is_dir():
            os.startfile(self.last_output_dir)

    def _close(self):
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()
