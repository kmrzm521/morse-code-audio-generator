"""Tkinter 图形界面及与界面无关的表单校验。"""

from __future__ import annotations

import os
import random
import tkinter as tk
import webbrowser
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
)
from .callsign_rules import global_entity_names
from .content import generate_until_duration, repeat_until_duration
from .exporters import ExportRequest, ExportResult, export_training_set
from .licensing import (
    is_current_machine_member,
    load_embedded_public_key,
    machine_code,
    save_activation,
    verify_activation,
)
from .settings import AppSettings, load_settings, save_settings, validate_settings


MODE_LABELS = {
    "随机字母": "letters",
    "随机数字": "numbers",
    "字母数字混合": "mixed",
    "标点符号": "punctuation",
    "通联符号": "prosigns",
    "无线电简语": "q_codes",
    "中国模拟呼号": "chinese_callsign",
    "全球模拟呼号": "global_callsign",
    "自定义文本": "custom",
}
MODE_NAMES = {value: key for key, value in MODE_LABELS.items()}
NUMBER_STYLE_LABELS = {"长码": "long", "短码": "short"}
OUTPUT_FORMAT_LABELS = {"MP3": "mp3", "WAV": "wav"}
NUMBER_STYLE_ALIASES = {"普通数字": "long", "缩短数字": "short"}
OUTPUT_FORMAT_ALIASES = {"压缩音频": "mp3", "波形音频": "wav"}
MEMBERSHIP_EMAIL = "kmrzm520@gmail.com"
PROJECT_URL = "https://github.com/kmrzm521/morse-code-audio-generator"
MEMBERSHIP_GUIDE = (
    "永久会员获取方式：\n"
    "1. 在 GitHub 赞助本项目。\n"
    f"2. 将 GitHub 用户名和本机机器码发送到 {MEMBERSHIP_EMAIL}。\n"
    "3. 赞助记录核实后，永久激活码将通过邮件回复。"
)
RANDOM_GLOBAL_ENTITY = "随机全球地区"
COUNTRIES = (RANDOM_GLOBAL_ENTITY, *global_entity_names())


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    text: str
    export: ExportRequest


def _number(values: Mapping[str, object], name: str, display: str, cast):
    try:
        return cast(values[name])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{display}必须是数字") from error


def _repeat_callsigns(
    factory,
    target_seconds: int,
    wpm: int,
    effective_wpm: int | None,
    number_style: str,
) -> str:
    return repeat_until_duration(
        factory,
        target_seconds,
        {
            "character_wpm": wpm,
            "effective_wpm": effective_wpm,
            "number_style": number_style,
        },
    )


def build_generation_request(
    values: Mapping[str, object],
    rng: random.Random | None = None,
    *,
    is_member: bool = False,
) -> GenerationRequest:
    """校验表单并一次性确定本次生成内容。"""
    rng = rng or random.Random()
    mode = str(values.get("mode", ""))
    group_size = _number(values, "group_size", "每组字符数", int)
    duration_seconds = _number(values, "duration_seconds", "生成时长", int)
    character_wpm = _number(values, "character_wpm", "字符速度", int)
    effective_value = _number(values, "effective_wpm", "间隔降速", int)
    frequency_hz = _number(values, "frequency_hz", "音调频率", int)
    farnsworth_enabled = bool(values.get("farnsworth_enabled", False))
    effective_wpm = effective_value if farnsworth_enabled else None
    number_style_value = str(values.get("number_style", "长码"))
    number_style = NUMBER_STYLE_LABELS.get(
        number_style_value, NUMBER_STYLE_ALIASES.get(number_style_value, number_style_value)
    )
    output_format_value = str(values.get("output_format", "MP3"))
    output_format = OUTPUT_FORMAT_LABELS.get(
        output_format_value, OUTPUT_FORMAT_ALIASES.get(output_format_value, output_format_value)
    ).lower()
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
    validate_settings(settings, is_member=is_member)
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
        entity = settings.country
        if entity == RANDOM_GLOBAL_ENTITY:
            entity = rng.choice(global_entity_names())
        text = _repeat_callsigns(
            lambda: generate_global_callsign(entity, rng),
            duration_seconds, character_wpm, effective_wpm, number_style,
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
    stem = f"{MODE_NAMES[mode]}_每分钟{character_wpm}字_{frequency_hz}赫兹_{timestamp}"
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
        self.root.title("摩斯电码生成器第六版（离线版）")
        self.root.geometry("820x760")
        self.root.minsize(760, 680)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="morse-export")
        self.future: Future[ExportResult] | None = None
        self.last_output_dir: Path | None = None
        self.settings = load_settings()
        self.is_member = is_current_machine_member()
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
        membership = ttk.Frame(outer)
        membership.grid(row=row, column=0, columnspan=2, sticky="ew", pady=4)
        self.member_status_var = tk.StringVar(
            value="永久会员" if self.is_member else "普通用户（每次最多五分钟）"
        )
        ttk.Label(membership, text="会员状态").pack(side="left")
        ttk.Label(membership, textvariable=self.member_status_var).pack(
            side="left", padx=(8, 16)
        )
        ttk.Button(membership, text="会员激活", command=self._show_activation).pack(
            side="left"
        )

        row += 1
        options = ttk.Frame(outer)
        options.grid(row=row, column=0, columnspan=2, sticky="ew")
        for column in range(6):
            options.columnconfigure(column, weight=1)
        ttk.Label(options, text="每组字符").grid(row=0, column=0)
        ttk.Spinbox(options, from_=1, to=20, width=7, textvariable=self._var("group_size", "5")).grid(row=0, column=1)
        ttk.Label(options, text="时长（秒）").grid(row=0, column=2)
        ttk.Entry(options, width=8, textvariable=self._var("duration_seconds", "60")).grid(row=0, column=3)
        ttk.Label(options, text="字符速度（字/分钟）").grid(row=0, column=4)
        ttk.Spinbox(options, from_=5, to=60, width=7, textvariable=self._var("character_wpm", "15")).grid(row=0, column=5)

        row += 1
        timing = ttk.Frame(outer)
        timing.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)
        self.farnsworth_check = ttk.Checkbutton(
            timing, text="间隔降速", variable=self._var("farnsworth_enabled", False, tk.BooleanVar),
            command=self._update_control_states,
        )
        self.farnsworth_check.pack(side="left")
        ttk.Label(timing, text="间隔速度（字/分钟）").pack(side="left", padx=(12, 4))
        self.effective_spin = ttk.Spinbox(timing, from_=1, to=59, width=7, textvariable=self._var("effective_wpm", "10"))
        self.effective_spin.pack(side="left")
        ttk.Label(timing, text="音调（赫兹）").pack(side="left", padx=(20, 4))
        ttk.Spinbox(timing, from_=300, to=1200, width=8, textvariable=self._var("frequency_hz", "700")).pack(side="left")

        row += 1
        selectors = ttk.Frame(outer)
        selectors.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Label(selectors, text="数字编码").pack(side="left")
        ttk.Combobox(selectors, state="readonly", width=10, values=tuple(NUMBER_STYLE_LABELS), textvariable=self._var("number_style", "长码")).pack(side="left", padx=5)
        ttk.Label(selectors, text="格式").pack(side="left", padx=(20, 4))
        ttk.Combobox(selectors, state="readonly", width=10, values=tuple(OUTPUT_FORMAT_LABELS), textvariable=self._var("output_format", "MP3")).pack(side="left")

        row += 1
        self.callsign_frame = ttk.LabelFrame(outer, text="呼号设置", padding=8)
        self.callsign_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Label(self.callsign_frame, text="省份").grid(row=0, column=0)
        self.province_box = ttk.Combobox(self.callsign_frame, state="readonly", values=list(CHINA_PROVINCE_RANGES), textvariable=self._var("province", "北京"), width=12)
        self.province_box.grid(row=0, column=1, padx=5)
        ttk.Label(self.callsign_frame, text="台站字母").grid(row=0, column=2)
        self.station_box = ttk.Combobox(self.callsign_frame, state="readonly", values=tuple("GHIDABCEFKLR"), textvariable=self._var("station_type", "G"), width=6)
        self.station_box.grid(row=0, column=3, padx=5)
        ttk.Label(self.callsign_frame, text="国家或地区").grid(row=0, column=4)
        self.country_box = ttk.Combobox(self.callsign_frame, state="readonly", values=COUNTRIES, textvariable=self._var("country", "中国"), width=30)
        self.country_box.grid(row=0, column=5, padx=5)
        ttk.Label(
            self.callsign_frame,
            text="按国际前缀及地区格式模拟生成，不代表真实签发",
        ).grid(row=1, column=0, columnspan=6, sticky="w", pady=(8, 0))

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
        self.generate_button = ttk.Button(buttons, text="生成音频和同步字幕", command=self._start_generation)
        self.generate_button.pack(side="left", padx=5)
        self.open_button = ttk.Button(buttons, text="打开输出文件夹", command=self._open_output, state="disabled")
        self.open_button.pack(side="left", padx=5)

    def _load_variables(self):
        values = asdict(self.settings)
        self.variables["mode_label"].set(MODE_NAMES.get(self.settings.mode, "随机字母"))
        for name, value in values.items():
            if name in self.variables:
                self.variables[name].set(value)
        inverse_number_styles = {value: label for label, value in NUMBER_STYLE_LABELS.items()}
        inverse_output_formats = {value: label for label, value in OUTPUT_FORMAT_LABELS.items()}
        self.variables["number_style"].set(
            inverse_number_styles.get(self.settings.number_style, "长码")
        )
        self.variables["output_format"].set(
            inverse_output_formats.get(self.settings.output_format, "MP3")
        )
        if self.variables["country"].get() not in COUNTRIES:
            self.variables["country"].set("中国")
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

    def _form_values(self) -> dict[str, object]:
        values = {name: variable.get() for name, variable in self.variables.items()}
        values["mode"] = self._mode()
        values["custom_text"] = self.custom_text.get("1.0", "end-1c")
        return values

    def _choose_output_dir(self):
        chosen = filedialog.askdirectory(title="选择输出目录")
        if chosen:
            self.variables["output_dir"].set(chosen)

    def _set_preview(self, text: str):
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    def _start_generation(self):
        try:
            request = build_generation_request(
                self._form_values(),
                is_member=self.is_member,
            )
            settings_values = self._form_values()
            save_settings(AppSettings(
                mode=self._mode(),
                group_size=int(settings_values["group_size"]),
                duration_seconds=int(settings_values["duration_seconds"]),
                character_wpm=int(settings_values["character_wpm"]),
                farnsworth_enabled=bool(settings_values["farnsworth_enabled"]),
                effective_wpm=int(settings_values["effective_wpm"]),
                frequency_hz=int(settings_values["frequency_hz"]),
                number_style=NUMBER_STYLE_LABELS[str(settings_values["number_style"])],
                output_format=OUTPUT_FORMAT_LABELS[str(settings_values["output_format"])],
                output_dir=str(settings_values["output_dir"]),
                province=str(settings_values["province"]),
                country=str(settings_values["country"]),
                station_type=str(settings_values["station_type"]),
                callsign_file="",
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
                f"音频：{result.audio_path}\n同步字幕：{result.lrc_path}",
                parent=self.root,
            )
        finally:
            self.future = None

    def _open_output(self):
        if self.last_output_dir is not None and self.last_output_dir.is_dir():
            os.startfile(self.last_output_dir)

    def _show_activation(self):
        window = tk.Toplevel(self.root)
        window.title("永久会员激活")
        window.geometry("720x460")
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        try:
            current_machine = machine_code()
        except ValueError as error:
            messagebox.showerror("机器码错误", str(error), parent=window)
            window.destroy()
            return

        machine_var = tk.StringVar(value=current_machine)
        activation_var = tk.StringVar()
        result_var = tk.StringVar(value="请输入永久激活码")
        ttk.Label(frame, text="本机机器码").grid(row=0, column=0, sticky="w", pady=8)
        ttk.Entry(frame, textvariable=machine_var, state="readonly").grid(
            row=0, column=1, sticky="ew", pady=8
        )

        def copy_machine_code():
            window.clipboard_clear()
            window.clipboard_append(current_machine)
            result_var.set("机器码已复制")

        ttk.Button(frame, text="复制机器码", command=copy_machine_code).grid(
            row=1, column=0, columnspan=2, pady=6
        )
        ttk.Label(frame, text=MEMBERSHIP_GUIDE, justify="left").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=8
        )

        def copy_email():
            window.clipboard_clear()
            window.clipboard_append(MEMBERSHIP_EMAIL)
            result_var.set("邮箱地址已复制")

        contact_buttons = ttk.Frame(frame)
        contact_buttons.grid(row=3, column=0, columnspan=2, pady=6)
        ttk.Button(contact_buttons, text="复制邮箱地址", command=copy_email).pack(
            side="left", padx=5
        )
        ttk.Button(
            contact_buttons,
            text="打开项目主页",
            command=lambda: webbrowser.open(PROJECT_URL),
        ).pack(side="left", padx=5)

        ttk.Label(frame, text="永久激活码").grid(row=4, column=0, sticky="w", pady=8)
        ttk.Entry(frame, textvariable=activation_var).grid(
            row=4, column=1, sticky="ew", pady=8
        )

        def activate():
            code = activation_var.get().strip()
            if not verify_activation(code, current_machine, load_embedded_public_key()):
                result_var.set("激活码无效或不适用于本机")
                return
            save_activation(code)
            self.is_member = True
            self.member_status_var.set("永久会员")
            result_var.set("永久会员激活成功")
            messagebox.showinfo("激活成功", "本机已成为永久会员", parent=window)

        ttk.Button(frame, text="立即激活", command=activate).grid(
            row=5, column=0, columnspan=2, pady=8
        )
        ttk.Label(frame, textvariable=result_var).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=8
        )

    def _close(self):
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()
