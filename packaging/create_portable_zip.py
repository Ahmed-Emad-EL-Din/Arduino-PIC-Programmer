"""Create a compact, validated Windows onedir archive.

The archive contains only PyInstaller's app executable and its runtime folder.
The runtime folder itself is already curated by ardpicprog.spec; this step uses
maximum Deflate compression and omits generated caches/debug-only files.
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

EXPECTED_ROOT = {"Arduino-PIC-Programmer.exe", "_internal"}
IGNORED_DIRS = {"__pycache__"}
IGNORED_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".pdb", ".ilk", ".obj", ".exp", ".lib", ".map"}
REQUIRED_ENTRIES = {
    "Arduino-PIC-Programmer.exe",
    "_internal/tools/ardpicprog.exe",
    "_internal/tools/avrdude/avrdude.exe",
    "_internal/tools/avrdude/avrdude.conf",
    "_internal/docs/USER_GUIDE.md",
    "_internal/assets/app-icon.ico",
    "_internal/assets/reference/ArdPicProg.jpg",
    "_internal/assets/reference/ArdPicProg_1_8_horo.png",
    "_internal/licenses/LICENSE",
    "_internal/licenses/LGPL-3.0.txt",
    "_internal/licenses/THIRD_PARTY_NOTICES.md",
    "_internal/licenses/COPYING",
    "_internal/licenses/UPSTREAM.md",
}
REQUIRED_FIRMWARE = {
    f"_internal/firmware/precompiled/{board}.hex"
    for board in (
        "uno", "nano_new", "nano_old", "pro_mini_5v",
        "mega2560", "leonardo", "micro",
    )
}


def _included_files(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in relative.parts):
            continue
        if not path.is_file() or path.name in IGNORED_NAMES:
            continue
        if path.suffix.lower() in IGNORED_SUFFIXES:
            continue
        files.append(path)
    return files


def create_portable_zip(source: Path, destination: Path) -> tuple[int, int, int]:
    source = source.resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"PyInstaller package directory does not exist: {source}")

    top_level = {entry.name for entry in source.iterdir()}
    if top_level != EXPECTED_ROOT:
        raise ValueError(
            "Portable package root must contain only the app EXE and _internal; "
            f"found: {sorted(top_level)}"
        )

    files = _included_files(source)
    archive_names = {path.relative_to(source).as_posix() for path in files}
    required = REQUIRED_ENTRIES | REQUIRED_FIRMWARE
    missing = sorted(required - archive_names)
    if missing:
        raise ValueError(f"Portable package is missing required runtime files: {missing}")
    if not any(
        name.startswith("_internal/") and name.endswith("/qwindows.dll")
        for name in archive_names
    ):
        raise ValueError("Portable package is missing Qt's qwindows.dll platform plugin")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    source_bytes = sum(path.stat().st_size for path in files)
    with zipfile.ZipFile(
        destination,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=False,
    ) as archive:
        for path in files:
            archive.write(
                path,
                arcname=path.relative_to(source).as_posix(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )

    with zipfile.ZipFile(destination, "r") as archive:
        if archive.testzip() is not None:
            raise ValueError("Portable ZIP failed its CRC integrity check")
        names = set(archive.namelist())
        archive_roots = {name.split("/", 1)[0] for name in names}
        if archive_roots != EXPECTED_ROOT:
            raise ValueError(f"Unexpected ZIP root entries: {sorted(archive_roots)}")
        if not required.issubset(names):
            raise ValueError("Portable ZIP does not contain all required runtime files")

    return source_bytes, destination.stat().st_size, len(files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_bytes, zip_bytes, file_count = create_portable_zip(args.source, args.output)
    saved = max(0.0, (1 - zip_bytes / source_bytes) * 100) if source_bytes else 0.0
    print(
        f"Validated compact portable ZIP: {file_count} runtime files, "
        f"{source_bytes:,} bytes raw → {zip_bytes:,} bytes ZIP ({saved:.1f}% smaller)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
