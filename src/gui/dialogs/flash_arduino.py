"""Arduino firmware upload dialog."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                               QLabel, QMessageBox, QPushButton, QVBoxLayout)
from core.avrdude import BOARDS, BOARD_BY_KEY, FlashError, flash_firmware
from core.serial_link import LinkError, list_serial_ports


class FlashArduinoDialog(QDialog):
    flashed = Signal(str, str)

    def __init__(self, settings, lane=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Flash ProgramPic firmware")
        self.settings = settings
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        note = QLabel(
            "Uploading replaces the sketch on the selected Arduino. The board must match the selected bootloader setting. "
            "Remove any reset capacitor while flashing, then reinstall it only after upload completes."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        form = QFormLayout()
        self.board = QComboBox()
        for b in BOARDS:
            self.board.addItem(b.label, b.key)
        idx = self.board.findData(settings.board_key)
        self.board.setCurrentIndex(max(0, idx))
        self.port = QComboBox()
        self.rescan = QPushButton("Rescan")
        self.rescan.clicked.connect(self._rescan)
        form.addRow("Board:", self.board)
        form.addRow("Port:", self.port)
        form.addRow("", self.rescan)
        layout.addLayout(form)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.flash_button = buttons.addButton("Flash Firmware", QDialogButtonBox.ButtonRole.ApplyRole)
        self.flash_button.clicked.connect(self._flash)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.reject)
        layout.addWidget(buttons)
        self._rescan()

    def _rescan(self) -> None:
        previous = self.settings.port
        self.port.clear()
        try:
            ports = list_serial_ports()
        except LinkError as exc:
            self.status.setText(str(exc))
            return
        for item in ports:
            self.port.addItem(item.label(), item.device)
        if not ports:
            self.port.addItem("No serial ports found", "")
        index = self.port.findData(previous)
        if index >= 0:
            self.port.setCurrentIndex(index)

    def _flash(self) -> None:
        key = str(self.board.currentData() or "")
        port = str(self.port.currentData() or "")
        if not port:
            QMessageBox.warning(self, "Select a port", "Connect the Arduino and select its serial port.")
            return
        board = BOARD_BY_KEY.get(key)
        if board is None:
            return
        answer = QMessageBox.warning(
            self, "Upload firmware?",
            f"Upload ProgramPic firmware to {board.label} on {port}? This replaces the sketch on that board.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.flash_button.setEnabled(False)
        self.status.setText("Uploading firmware…")
        try:
            output = flash_firmware(key, port)
        except FlashError as exc:
            self.status.setText(str(exc))
            QMessageBox.critical(self, "Firmware upload failed", str(exc))
        else:
            self.settings.board_key = key
            self.settings.port = port
            self.settings.sync()
            self.status.setText(output or "Firmware upload completed.")
            self.flashed.emit(port, key)
            QMessageBox.information(self, "Firmware uploaded", self.status.text())
        finally:
            self.flash_button.setEnabled(True)
