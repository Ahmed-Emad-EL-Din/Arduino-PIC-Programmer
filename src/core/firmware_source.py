"""Read, save, restore, and export the editable ProgramPic sketch."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QStandardPaths


class FirmwareSourceStore:
    def __init__(self, bundled_path: Path | None = None, user_path: Path | None = None) -> None:
        if bundled_path is None:
            if getattr(sys, "frozen", False):
                root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
            else:
                root = Path(__file__).resolve().parents[2]
            bundled_path = root / "firmware" / "source" / "ProgramPic" / "ProgramPic.ino"
        if user_path is None:
            config_dir = Path(QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppConfigLocation
            ))
            user_path = config_dir / "firmware" / "ProgramPic.ino"
        self.bundled_path = Path(bundled_path)
        self.user_path = Path(user_path)

    @property
    def has_custom_source(self) -> bool:
        return self.user_path.is_file()

    def bundled_source(self) -> str:
        return self.bundled_path.read_text(encoding="utf-8")

    def load(self) -> str:
        path = self.user_path if self.has_custom_source else self.bundled_path
        return path.read_text(encoding="utf-8")

    def save(self, source: str) -> Path:
        if not source.strip():
            raise ValueError("Firmware source cannot be empty.")
        self.user_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix="ProgramPic-", suffix=".ino", dir=self.user_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(source)
            Path(temp_name).replace(self.user_path)
        except Exception:
            Path(temp_name).unlink(missing_ok=True)
            raise
        return self.user_path

    def reset(self) -> None:
        self.user_path.unlink(missing_ok=True)

    @staticmethod
    def export(source: str, destination: Path) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source, encoding="utf-8", newline="\n")
        return destination
