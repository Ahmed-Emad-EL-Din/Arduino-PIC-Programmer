import importlib.util
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "packaging" / "create_installer_zip.py"
SPEC = importlib.util.spec_from_file_location("create_installer_zip", SCRIPT_PATH)
installer_zip_builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer_zip_builder)


def test_installer_zip_contains_only_the_setup_executable(tmp_path):
    installer = tmp_path / installer_zip_builder.INSTALLER_NAME
    installer.write_bytes(b"setup executable contents")
    output = tmp_path / "release" / "installer-only.zip"

    source_size, archive_size = installer_zip_builder.create_installer_zip(installer, output)

    assert source_size == installer.stat().st_size
    assert archive_size == output.stat().st_size
    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == [installer_zip_builder.INSTALLER_NAME]
        assert archive.read(installer_zip_builder.INSTALLER_NAME) == installer.read_bytes()
        assert archive.testzip() is None


def test_installer_zip_rejects_unexpected_installer_name(tmp_path):
    installer = tmp_path / "portable-app.exe"
    installer.write_bytes(b"setup")
    try:
        installer_zip_builder.create_installer_zip(installer, tmp_path / "installer.zip")
    except ValueError as exc:
        assert "must be named" in str(exc)
    else:
        raise AssertionError("Unexpected installer names must be rejected")


def test_installer_zip_rejects_missing_installer(tmp_path):
    try:
        installer_zip_builder.create_installer_zip(
            tmp_path / installer_zip_builder.INSTALLER_NAME,
            tmp_path / "installer.zip",
        )
    except FileNotFoundError as exc:
        assert "does not exist" in str(exc)
    else:
        raise AssertionError("Missing installer inputs must be rejected")
