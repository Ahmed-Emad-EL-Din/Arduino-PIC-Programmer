"""Settings editor with apply-on-accept behavior."""
from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFormLayout, QLabel, QVBoxLayout)
from core.avrdude import BOARDS
from core.serial_config import PROGRAMMER_BAUD


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Programmer Settings")
        self.settings = settings
        form = QFormLayout()
        self.theme = QComboBox()
        self.theme.addItem("Dark", "dark")
        self.theme.addItem("Light", "light")
        self.theme.addItem("High contrast", "high_contrast")
        self.theme.setCurrentIndex(max(0, self.theme.findData(settings.theme)))
        self.theme.setToolTip(
            "Changes appearance only. The manual high-contrast palette uses a black background, "
            "white text, and bright focus/status colors."
        )
        form.addRow("Appearance:", self.theme)
        self.board = QComboBox()
        for board in BOARDS:
            self.board.addItem(board.label, board.key)
        self.board.setCurrentIndex(max(0, self.board.findData(settings.board_key)))
        self.board.setToolTip(
            "Selects the wiring reference and Nano bootloader profile; it does not detect the board. "
            "The 9600-baud ProgramPic link is independent of bootloader upload speed."
        )
        form.addRow("Arduino board:", self.board)
        self.mcu = QComboBox()
        # avoid a circular import from the workbench
        from core.mcu_db import all_devices
        for dev in all_devices():
            self.mcu.addItem(dev.display_name, dev.name)
        self.mcu.setCurrentIndex(max(0, self.mcu.findData(settings.mcu)))
        form.addRow("Default target:", self.mcu)
        self.baud = QLabel(f"{PROGRAMMER_BAUD} baud (required by ProgramPic)")
        self.baud.setAccessibleName("ProgramPic runtime serial speed")
        self.baud.setToolTip(
            "Fixed at 9600 baud by the bundled ProgramPic firmware. "
            "Arduino bootloader upload speed is configured separately."
        )
        form.addRow("ProgramPic link:", self.baud)
        self.verify = QCheckBox("Read back and compare after programming")
        self.verify.setChecked(settings.auto_verify)
        self.verify.setToolTip("When off, a completed write is not evidence that the target stored the data correctly.")
        form.addRow("Verification:", self.verify)
        self.confirm = QCheckBox("Confirm destructive operations")
        self.confirm.setChecked(settings.confirm_erase)
        self.confirm.setToolTip("Adds an explicit confirmation before erase/write operations. Hardware preflight still applies.")
        form.addRow("Confirmations:", self.confirm)
        self.log_visible = QCheckBox("Show activity log at startup")
        self.log_visible.setChecked(settings.log_visible)
        self.log_visible.setToolTip("The log records local session messages and can be exported from the File menu.")
        form.addRow("Activity log:", self.log_visible)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _save(self) -> None:
        self.settings.theme = self.theme.currentData()
        self.settings.board_key = self.board.currentData()
        self.settings.mcu = self.mcu.currentData()
        self.settings.auto_verify = self.verify.isChecked()
        self.settings.confirm_erase = self.confirm.isChecked()
        self.settings.log_visible = self.log_visible.isChecked()
        self.settings.sync()
        self.accept()
