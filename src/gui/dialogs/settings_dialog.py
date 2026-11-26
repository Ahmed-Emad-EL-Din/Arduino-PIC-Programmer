"""Settings editor with apply-on-accept behavior."""
from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFormLayout, QSpinBox, QVBoxLayout)
from core.avrdude import BOARDS


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Programmer Settings")
        self.settings = settings
        form = QFormLayout()
        self.theme = QComboBox()
        self.theme.addItem("Dark", "dark")
        self.theme.addItem("Light", "light")
        self.theme.setCurrentIndex(max(0, self.theme.findData(settings.theme)))
        self.theme.setToolTip("Changes appearance only; status text remains explicit in both themes.")
        form.addRow("Appearance:", self.theme)
        self.board = QComboBox()
        for board in BOARDS:
            self.board.addItem(board.label, board.key)
        self.board.setCurrentIndex(max(0, self.board.findData(settings.board_key)))
        self.board.setToolTip("Selects the wiring reference; it does not detect which board is connected.")
        form.addRow("Arduino board:", self.board)
        self.mcu = QComboBox()
        # avoid a circular import from the workbench
        from core.mcu_db import all_devices
        for dev in all_devices():
            self.mcu.addItem(dev.display_name, dev.name)
        self.mcu.setCurrentIndex(max(0, self.mcu.findData(settings.mcu)))
        form.addRow("Default target:", self.mcu)
        self.baud = QSpinBox()
        self.baud.setRange(9600, 1000000)
        self.baud.setValue(settings.baud)
        self.baud.setToolTip("ProgramPic host-link speed; default firmware now uses 9600 baud. This is separate from the Nano bootloader upload speed.")
        form.addRow("Serial speed:", self.baud)
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
        self.settings.baud = self.baud.value()
        self.settings.auto_verify = self.verify.isChecked()
        self.settings.confirm_erase = self.confirm.isChecked()
        self.settings.log_visible = self.log_visible.isChecked()
        self.settings.sync()
        self.accept()
