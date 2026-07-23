# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path


python_base = Path(sys.base_prefix)
tcl_root = python_base / "tcl"
dll_root = python_base / "DLLs"

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[
        (str(dll_root / "_tkinter.pyd"), "."),
        (str(dll_root / "tcl86t.dll"), "."),
        (str(dll_root / "tk86t.dll"), "."),
    ],
    datas=[
        (str(tcl_root / "tcl8.6"), "_tcl_data"),
        (str(tcl_root / "tk8.6"), "_tk_data"),
    ],
    hiddenimports=[
        "lameenc",
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.ttk",
    ],
    hookspath=["packaging_hooks"],
    hooksconfig={},
    runtime_hooks=["packaging_hooks/pyi_rth_tkinter_manual.py"],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="摩斯电码生成器",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
