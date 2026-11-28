"""Package the Windows setup executable as the only ZIP member."""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

INSTALLER_NAME = "Arduino-PIC-Programmer-Setup-x64.exe"


def create_installer_zip(installer: Path, destination: Path) -> tuple[int, int]:
    installer = installer.resolve()
    destination = destination.resolve()
    if not installer.is_file():
        raise FileNotFoundError(f"Windows installer does not exist: {installer}")
    if installer.name != INSTALLER_NAME:
        raise ValueError(f"Installer must be named {INSTALLER_NAME}; found {installer.name}")
    if installer == destination:
        raise ValueError("ZIP output must not overwrite the installer")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    installer_size = installer.stat().st_size

    # The Inno Setup executable is already compressed; storing it avoids
    # spending CPU and usually avoids adding a second, useless compression layer.
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.write(installer, arcname=INSTALLER_NAME)

    with zipfile.ZipFile(destination, "r") as archive:
        if archive.testzip() is not None:
            raise ValueError("Installer ZIP failed its CRC integrity check")
        if archive.namelist() != [INSTALLER_NAME]:
            raise ValueError("Installer ZIP must contain only the setup executable")
        with archive.open(INSTALLER_NAME) as zipped, installer.open("rb") as original:
            while chunk := original.read(1024 * 1024):
                if zipped.read(len(chunk)) != chunk:
                    raise ValueError("Installer ZIP contents do not match the setup executable")
            if zipped.read(1):
                raise ValueError("Installer ZIP contains unexpected trailing setup data")

    return installer_size, destination.stat().st_size


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_size, zip_size = create_installer_zip(args.installer, args.output)
    print(
        f"Validated installer-only ZIP: {INSTALLER_NAME} "
        f"({source_size:,} bytes; archive {zip_size:,} bytes)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
