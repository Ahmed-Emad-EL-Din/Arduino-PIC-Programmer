import importlib.util
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "packaging" / "create_portable_zip.py"
SPEC = importlib.util.spec_from_file_location("create_portable_zip", SCRIPT_PATH)
zip_builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(zip_builder)


def _write(path: Path, content: bytes = b"runtime-data") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _make_minimal_package(root: Path) -> None:
    _write(root / "Arduino-PIC-Programmer.exe")
    _write(root / "_internal" / "tools" / "ardpicprog.exe")
    _write(root / "_internal" / "tools" / "avrdude" / "avrdude.exe")
    _write(root / "_internal" / "tools" / "avrdude" / "avrdude.conf")
    _write(root / "_internal" / "docs" / "USER_GUIDE.md")
    _write(root / "_internal" / "assets" / "app-icon.ico")
    _write(root / "_internal" / "assets" / "reference" / "ArdPicProg.jpg")
    _write(root / "_internal" / "assets" / "reference" / "ArdPicProg_1_8_horo.png")
    for license_file in (
        "LICENSE", "LGPL-3.0.txt", "THIRD_PARTY_NOTICES.md", "COPYING", "UPSTREAM.md"
    ):
        _write(root / "_internal" / "licenses" / license_file)
    for board in (
        "uno", "nano_new", "nano_old", "pro_mini_5v", "mega2560", "leonardo", "micro"
    ):
        _write(root / "_internal" / "firmware" / "precompiled" / f"{board}.hex")
    _write(root / "_internal" / "PySide6" / "Qt" / "plugins" / "platforms" / "qwindows.dll")


def test_portable_zip_uses_max_deflate_and_excludes_build_cruft(tmp_path):
    package = tmp_path / "package"
    _make_minimal_package(package)
    _write(package / "_internal" / "cache" / "__pycache__" / "temp.pyc", b"cache")
    _write(package / "_internal" / "debug.pdb", b"debug-symbols")
    _write(package / "_internal" / "runtime.bin", b"A" * 100_000)
    output = tmp_path / "dist" / "portable.zip"

    raw_size, zip_size, count = zip_builder.create_portable_zip(package, output)

    assert output.is_file()
    assert zip_size < raw_size
    assert count > 0
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert "Arduino-PIC-Programmer.exe" in names
        assert "_internal/runtime.bin" in names
        assert not any("__pycache__" in name or name.endswith((".pyc", ".pdb")) for name in names)
        assert {name.split("/", 1)[0] for name in names} == zip_builder.EXPECTED_ROOT
        assert all(info.compress_type == zipfile.ZIP_DEFLATED for info in archive.infolist())


def test_portable_zip_rejects_unexpected_package_root(tmp_path):
    package = tmp_path / "package"
    _make_minimal_package(package)
    _write(package / "README.md")

    try:
        zip_builder.create_portable_zip(package, tmp_path / "portable.zip")
    except ValueError as exc:
        assert "must contain only" in str(exc)
    else:
        raise AssertionError("Unexpected top-level files must be rejected")
