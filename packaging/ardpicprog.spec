# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the portable Windows desktop package.

The release is an onedir bundle: users extract the ZIP and launch the visible
Arduino-PIC-Programmer.exe. This avoids fragile one-file extraction for Qt,
firmware, and the ArdPicProg host helper.
"""
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent  # SPECPATH is the packaging directory
SRC = ROOT / "src"


def add_if_present(path: Path, destination: str, datas: list) -> None:
    if path.exists():
        datas.append((str(path), destination))


# Include runtime data and the editable ProgramPic source. Keep development
# docs, source assets, and build helpers out of the portable package.
datas = []
for path, destination in (
    (ROOT / "docs" / "USER_GUIDE.md", "docs"),
    (ROOT / "firmware" / "source" / "ProgramPic" / "ProgramPic.ino", "firmware/source/ProgramPic"),
    (ROOT / "assets" / "app-icon.ico", "assets"),
    (ROOT / "assets" / "reference" / "circuit-reference.png", "assets/reference"),
    (ROOT / "tools" / "ardpicprog.exe", "tools"),
    (ROOT / "tools" / "avrdude" / "avrdude.exe", "tools/avrdude"),
    (ROOT / "tools" / "avrdude" / "avrdude.conf", "tools/avrdude"),
    (ROOT / "tools" / "avrdude" / "AVRDUDE-LICENSE.txt", "licenses"),
    (ROOT / "vendor" / "ArdPicProg" / "COPYING", "licenses"),
    (ROOT / "vendor" / "ArdPicProg" / "UPSTREAM.md", "licenses"),
    (ROOT / "LICENSE", "licenses"),
    (ROOT / "LGPL-3.0.txt", "licenses"),
    (ROOT / "THIRD_PARTY_NOTICES.md", "licenses"),
):
    add_if_present(path, destination, datas)

for path in sorted((ROOT / "firmware" / "precompiled").glob("*.hex")):
    datas.append((str(path), "firmware/precompiled"))

for path in sorted((ROOT / "tools" / "avrdude").glob("*.dll")):
    datas.append((str(path), "tools/avrdude"))

hiddenimports = [
    "serial",
    "serial.tools.list_ports",
]

analysis = Analysis(
    [str(SRC / "main.py")],
    pathex=[str(SRC), str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pydoc_data"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Arduino-PIC-Programmer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / "assets" / "app-icon.ico"),
    version=str(ROOT / "packaging" / "version_info.txt"),
)
collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=False,
    name="Arduino-PIC-Programmer",
)
