# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — produces the publishable desktop EXE.

Build (Windows):   packaging\\build.bat
Build (Linux/mac): packaging/build.sh
CI:                .github/workflows/build-windows.yml
"""
import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent   # noqa: F821 — SPECPATH provided by PyInstaller
SRC = ROOT / "src"

block_cipher = None

datas = [
    (str(ROOT / "firmware" / "precompiled"), "firmware/precompiled"),
    (str(ROOT / "firmware" / "source"), "firmware/source"),
    (str(ROOT / "docs"), "docs"),
    (str(ROOT / "assets"), "assets"),
]

# bundle avrdude when present in tools/ (build scripts download it first)
tools = ROOT / "tools"
if tools.is_dir():
    datas.append((str(tools), "tools"))

hiddenimports = [
    "serial",
    "serial.tools.list_ports",
    "PySide6.QtSvg",
]

a = Analysis(
    [str(SRC / "main.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pydoc_data"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Arduino-PIC-Programmer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,               # GUI app — no console window
    disable_windowed_traceback=False,
    icon=str(ROOT / "assets" / "icon.ico") if sys.platform.startswith("win")
    else str(ROOT / "assets" / "icon.png"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Arduino-PIC-Programmer",
)
