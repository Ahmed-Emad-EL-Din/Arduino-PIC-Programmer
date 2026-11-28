"""Asynchronous Arduino firmware upload dialog."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from .scrollable import fit_dialog_to_screen, scrollable_content

from app.diagnostics import report_exception, show_diagnostic_error
from core.avrdude import BOARDS, BOARD_BY_KEY, FlashResult, flash_firmware
from core.serial_link import LinkError, list_serial_ports
from gui.dialogs.firmware_editor import FirmwareEditorDialog
from gui.workers import Worker


class FlashArduinoDialog(QDialog):
    flashed = Signal(str, str)

    def __init__(self, settings, lane=None, parent=None, board_key: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Flash ProgramPic firmware")
        self.settings = settings
        self.lane = lane
        self._worker: Worker | None = None
        self._upload_error = ""
        self._upload_output = ""
        self._upload_succeeded = False
        self._upload_port = ""
        self._upload_board_key = ""
        self._upload_board_label = ""
        self._upload_baud = 0
        self._upload_fallback_used = False
        self._uploading = False
        content = QWidget()
        content_layout = QVBoxLayout(content)
        note = QLabel(
            "Replaces the Arduino sketch. Nano upload tries 115200 first, then 57600 if sync fails. "
            "The ProgramPic runtime link uses 9600 baud; this is separate from upload speed. "
            "The Nano bootloader label reflects which upload speed succeeds."
        )
        note.setWordWrap(True)
        content_layout.addWidget(note)

        form = QFormLayout()
        self.board = QComboBox()
        for board in BOARDS:
            self.board.addItem(board.label, board.key)
        idx = self.board.findData(board_key or settings.board_key)
        self.board.setCurrentIndex(max(0, idx))
        self.port = QComboBox()
        self.rescan = QPushButton("Rescan")
        self.rescan.clicked.connect(self._rescan)
        form.addRow("Board:", self.board)
        form.addRow("Port:", self.port)
        form.addRow("", self.rescan)
        content_layout.addLayout(form)

        self.board_note = QLabel()
        self.board_note.setObjectName("warn")
        self.board_note.setWordWrap(True)
        content_layout.addWidget(self.board_note)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        content_layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        content_layout.addWidget(self.progress)

        layout = QVBoxLayout(self)
        layout.addWidget(scrollable_content(content), 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.edit_source_button = buttons.addButton("Edit Code…", QDialogButtonBox.ButtonRole.ActionRole)
        self.edit_source_button.clicked.connect(lambda: FirmwareEditorDialog(self).exec())
        self.flash_button = buttons.addButton("Flash Firmware", QDialogButtonBox.ButtonRole.ApplyRole)
        self.close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        self.flash_button.clicked.connect(self._flash)
        buttons.rejected.connect(self.reject)
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self.board.currentIndexChanged.connect(self._update_board_support)
        self._update_board_support()
        self._rescan()
        fit_dialog_to_screen(self, 620, 560, 420, 340)

    def _update_board_support(self) -> None:
        board = BOARD_BY_KEY.get(str(self.board.currentData() or ""))
        supported = bool(board and board.firmware_flash_supported)
        if board and not supported:
            self.board_note.setText(
                f"Firmware upload for {board.label} is not supported in this dialog. "
                "Use Arduino IDE to install ProgramPic; the board can still run it afterward."
            )
            self.board_note.show()
            self.flash_button.setToolTip("Use Arduino IDE for Leonardo/Micro firmware upload.")
        else:
            self.board_note.clear()
            self.board_note.hide()
            self.flash_button.setToolTip("")
        self.flash_button.setEnabled(supported and not self._uploading)

    def _rescan(self) -> None:
        previous = str(self.port.currentData() or self.settings.port or "")
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

    def _set_uploading(self, active: bool) -> None:
        self._uploading = active
        self.board.setEnabled(not active)
        self.port.setEnabled(not active)
        self.rescan.setEnabled(not active)
        self.close_button.setEnabled(not active)
        self.progress.setVisible(active)
        self._update_board_support()

    @staticmethod
    def _output_excerpt(output: str, limit: int = 5000) -> str:
        output = (output or "").strip()
        if len(output) <= limit:
            return output
        return "[Earlier avrdude output omitted]\n" + output[-limit:]

    def _on_upload_progress(self, message: str) -> None:
        if message:
            self.status.setText(message)

    def _on_upload_succeeded(self, result) -> None:
        if isinstance(result, FlashResult):
            self._upload_output = result.output
            self._upload_board_key = result.board_key
            self._upload_board_label = BOARD_BY_KEY[result.board_key].label
            self._upload_baud = result.baud
            self._upload_fallback_used = result.fallback_used
        else:  # Keep mocked/older result providers friendly to the UI.
            self._upload_output = str(result or "")
            board = BOARD_BY_KEY.get(self._upload_board_key)
            self._upload_baud = board.bootloader_baud if board else 0
            self._upload_fallback_used = False
        try:
            self.settings.board_key = self._upload_board_key
            self.settings.port = self._upload_port
            self.settings.sync()
        except Exception as exc:
            self._upload_error = report_exception("Saving firmware upload settings", exc)
            self.status.setText(self._output_excerpt(self._upload_error))
            return

        self._upload_succeeded = True
        fallback_note = (
            f" (auto-retried successfully at {self._upload_baud} baud)"
            if self._upload_fallback_used else ""
        )
        self.status.setText(
            f"Firmware upload completed for {self._upload_board_label} on "
            f"{self._upload_port}{fallback_note}."
        )
        self.flashed.emit(self._upload_port, self._upload_board_key)

    def _on_upload_failed(self, message: str) -> None:
        self._upload_error = str(message)
        self.status.setText(self._output_excerpt(self._upload_error))

    def _on_upload_finished(self) -> None:
        self._worker = None
        self._set_uploading(False)
        if self._upload_error:
            show_diagnostic_error(
                self,
                "Firmware upload failed",
                self._output_excerpt(self._upload_error),
                critical=True,
            )
        elif self._upload_succeeded:
            summary = (
                f"ProgramPic firmware uploaded to {self._upload_board_label} "
                f"on {self._upload_port} at {self._upload_baud} baud."
            )
            details = self._output_excerpt(self._upload_output)
            QMessageBox.information(
                self,
                "Firmware uploaded",
                summary + (f"\n\n{details}" if details else ""),
            )

    def _flash(self) -> None:
        if self._uploading:
            return
        if self.lane is not None and self.lane.busy:
            QMessageBox.information(
                self,
                "Programmer busy",
                "Wait for the current hardware operation to finish before uploading firmware.",
            )
            return

        key = str(self.board.currentData() or "")
        port = str(self.port.currentData() or "")
        if not port:
            QMessageBox.warning(self, "Select a port", "Connect the Arduino and select its serial port.")
            return
        board = BOARD_BY_KEY.get(key)
        if board is None or not board.firmware_flash_supported:
            return
        answer = QMessageBox.warning(
            self,
            "Upload firmware?",
            f"Upload ProgramPic firmware to {board.label} on {port}? This replaces the sketch on that board.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._upload_error = ""
        self._upload_output = ""
        self._upload_succeeded = False
        self._upload_port = port
        self._upload_board_key = key
        self._upload_board_label = board.label
        self.status.setText(
            f"Uploading to {board.label} on {port} at {board.bootloader_baud} baud. "
            "Keep the board connected; the window will remain responsive."
        )
        self._set_uploading(True)

        def upload(progress, _percent, _cancel):
            progress(f"Opening {port} and uploading ProgramPic…")
            return flash_firmware(key, port)

        worker = Worker(upload, name="Firmware upload", parent=self)
        self._worker = worker
        worker.progressed.connect(self._on_upload_progress)
        worker.succeeded.connect(self._on_upload_succeeded)
        worker.failed.connect(self._on_upload_failed)
        worker.finished.connect(self._on_upload_finished)
        try:
            if self.lane is not None:
                self.lane.start(worker)
            else:
                worker.start()
        except RuntimeError as exc:
            self._worker = None
            self._upload_error = report_exception("Starting firmware upload", exc)
            worker.deleteLater()
            self._set_uploading(False)
            self.status.setText(self._upload_error)
            show_diagnostic_error(
                self, "Firmware upload failed", self._upload_error, critical=True
            )

    def reject(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self.status.setText(
                "Upload is still running. Keep the Arduino connected until avrdude finishes."
            )
            return
        super().reject()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._worker is not None and self._worker.isRunning():
            self.status.setText(
                "Upload is still running. Keep the Arduino connected until avrdude finishes."
            )
            event.ignore()
            return
        super().closeEvent(event)
