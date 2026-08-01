"""所有者专用的永久会员激活码生成窗口。"""

from __future__ import annotations

import base64
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .licensing import sign_activation


def owner_private_key_path() -> Path:
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
    return base / "owner-private-key.txt"


def load_owner_private_key(path: Path) -> bytes:
    try:
        encoded = Path(path).read_text(encoding="ascii").strip()
        private_key = base64.b64decode(encoded, validate=True)
        Ed25519PrivateKey.from_private_bytes(private_key)
        return private_key
    except (OSError, UnicodeError, ValueError) as error:
        raise ValueError("私钥文件缺失或无效") from error


def create_activation(machine: str, private_path: Path) -> str:
    normalized = machine.strip().upper()
    if not re.fullmatch(r"[A-F0-9]{4}(?:-[A-F0-9]{4}){1,4}", normalized):
        raise ValueError("请输入正确的机器码")
    return sign_activation(normalized, load_owner_private_key(private_path))


class LicenseAdminApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("会员激活码生成工具")
        self.root.geometry("680x300")
        self.root.resizable(False, False)
        self.private_path = owner_private_key_path()
        self.machine_var = tk.StringVar()
        self.activation_var = tk.StringVar()
        self.status_var = tk.StringVar(value="请输入用户机器码")
        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="用户机器码").grid(row=0, column=0, sticky="w", pady=8)
        ttk.Entry(frame, textvariable=self.machine_var).grid(
            row=0, column=1, sticky="ew", pady=8
        )
        ttk.Button(frame, text="生成永久激活码", command=self._generate).grid(
            row=1, column=0, columnspan=2, pady=10
        )
        ttk.Label(frame, text="永久激活码").grid(row=2, column=0, sticky="w", pady=8)
        ttk.Entry(frame, textvariable=self.activation_var, state="readonly").grid(
            row=2, column=1, sticky="ew", pady=8
        )
        ttk.Button(frame, text="复制激活码", command=self._copy).grid(
            row=3, column=0, columnspan=2, pady=8
        )
        ttk.Label(frame, textvariable=self.status_var).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=8
        )

    def _generate(self) -> None:
        try:
            code = create_activation(self.machine_var.get(), self.private_path)
        except ValueError as error:
            self.status_var.set(str(error))
            messagebox.showerror("生成失败", str(error), parent=self.root)
            return
        self.activation_var.set(code)
        self.status_var.set("永久激活码已生成")

    def _copy(self) -> None:
        code = self.activation_var.get()
        if not code:
            self.status_var.set("请先生成永久激活码")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        self.status_var.set("永久激活码已复制")
