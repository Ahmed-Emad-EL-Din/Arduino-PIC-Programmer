"""Persistent user preferences using Qt's platform-native settings store."""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings

from app import APP_NAME, ORG_NAME


class AppSettings:
    def __init__(self) -> None:
        self._settings = QSettings(ORG_NAME, APP_NAME)
        self._settings.beginGroup("workbench")
        # Keep the host link aligned with the bundled firmware. Migrate known
        # legacy defaults once, preserving intentional custom baud selections.
        if not self._settings.value("baud_115200_migrated", False, type=bool):
            try:
                old_baud = int(self._settings.value("baud", 115200))
            except (TypeError, ValueError):
                old_baud = 115200
            if old_baud in (9600, 57600):
                self._settings.setValue("baud", 115200)
            self._settings.setValue("baud_115200_migrated", True)
            self._settings.sync()

    def _get(self, key, default):
        return self._settings.value(key, default)

    @property
    def theme(self) -> str:
        value = str(self._get("theme", "dark"))
        return value if value in ("dark", "light") else "dark"

    @theme.setter
    def theme(self, value: str) -> None:
        self._settings.setValue("theme", value if value in ("dark", "light") else "dark")

    @property
    def font_size(self) -> int:
        try:
            return max(9, min(14, int(self._get("font_size", 11))))
        except (TypeError, ValueError):
            return 11

    @font_size.setter
    def font_size(self, value: int) -> None:
        self._settings.setValue("font_size", max(9, min(14, int(value))))

    @property
    def board_key(self) -> str:
        return str(self._get("board_key", "uno"))

    @board_key.setter
    def board_key(self, value: str) -> None:
        self._settings.setValue("board_key", value)

    @property
    def mcu(self) -> str:
        return str(self._get("mcu", "pic16f84a"))

    @mcu.setter
    def mcu(self, value: str) -> None:
        self._settings.setValue("mcu", value)

    @property
    def port(self) -> str:
        return str(self._get("port", ""))

    @port.setter
    def port(self, value: str) -> None:
        self._settings.setValue("port", value)

    @property
    def baud(self) -> int:
        try:
            return int(self._get("baud", 115200))
        except (TypeError, ValueError):
            return 115200

    @baud.setter
    def baud(self, value: int) -> None:
        self._settings.setValue("baud", int(value))

    @property
    def auto_verify(self) -> bool:
        return self._settings.value("auto_verify", True, type=bool)

    @auto_verify.setter
    def auto_verify(self, value: bool) -> None:
        self._settings.setValue("auto_verify", bool(value))

    @property
    def confirm_erase(self) -> bool:
        return self._settings.value("confirm_erase", True, type=bool)

    @confirm_erase.setter
    def confirm_erase(self, value: bool) -> None:
        self._settings.setValue("confirm_erase", bool(value))

    @property
    def log_visible(self) -> bool:
        return self._settings.value("log_visible", False, type=bool)

    @log_visible.setter
    def log_visible(self, value: bool) -> None:
        self._settings.setValue("log_visible", bool(value))

    @property
    def geometry(self):
        return self._get("geometry", None)

    @geometry.setter
    def geometry(self, value) -> None:
        self._settings.setValue("geometry", value)

    @property
    def window_state(self):
        return self._get("window_state", None)

    @window_state.setter
    def window_state(self, value) -> None:
        self._settings.setValue("window_state", value)

    @property
    def recent_files(self):
        value = self._get("recent_files", [])
        return list(value) if isinstance(value, (list, tuple)) else []

    def add_recent(self, path: str) -> None:
        values = [path] + [p for p in self.recent_files if p != path]
        self._settings.setValue("recent_files", values[:10])

    def sync(self) -> None:
        self._settings.sync()
