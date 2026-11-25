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
        form.addRow("Appearance:", self.theme)
        self.board = QComboBox()
        for board in BOARDS:
            self.board.addItem(board.label, board.key)
        self.board.setCurrentIndex(max(0, self.board.findData(settings.board_key)))
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
        form.addRow("Serial speed:", self.baud)
        self.verify = QCheckBox("Read back and verify after programming")
        self.verify.setChecked(settings.auto_verify)
        form.addRow("Verification:", self.verify)
        self.confirm = QCheckBox("Confirm destructive operations")
        self.confirm.setChecked(settings.confirm_erase)
        form.addRow("Confirmations:", self.confirm)
        self.log_visible = QCheckBox("Show activity log at startup")
        self.log_visible.setChecked(settings.log_visible)
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
