"""Plain-text editor for the bundled ProgramPic sketch."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from core.firmware_source import FirmwareSourceStore


class FirmwareEditorDialog(QDialog):
    def __init__(self, parent=None, store: FirmwareSourceStore | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ProgramPic Source")
        self.resize(900, 680)
        self.store = store or FirmwareSourceStore()
        self._bundled = self.store.bundled_source()
        self._saved = self.store.load()

        layout = QVBoxLayout(self)
        note = QLabel("Save a local copy. Export and upload it with Arduino IDE; Flash Firmware uses the bundled build.")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.status = QLabel()
        layout.addWidget(self.status)
        self.editor = QPlainTextEdit()
        self.editor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setTabStopDistance(self.editor.fontMetrics().horizontalAdvance(" ") * 4)
        self.editor.setPlainText(self._saved)
        self.editor.textChanged.connect(self._update_status)
        layout.addWidget(self.editor, 1)

        actions = QHBoxLayout()
        self.reset_button = QPushButton("Reset to Default")
        self.reset_button.clicked.connect(self._reset)
        self.export_button = QPushButton("Export Sketch…")
        self.export_button.clicked.connect(self._export)
        actions.addWidget(self.reset_button)
        actions.addWidget(self.export_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.save_button = buttons.addButton("Save", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self._close)
        self.save_button.clicked.connect(self._save)
        layout.addWidget(buttons)
        self._update_status()

    def _is_dirty(self) -> bool:
        return self.editor.toPlainText() != self._saved

    def _update_status(self) -> None:
        if self._is_dirty():
            self.status.setText("Unsaved changes")
        elif self.store.has_custom_source:
            self.status.setText("Using your saved copy")
        else:
            self.status.setText("Using bundled source")
        self.save_button.setEnabled(self._is_dirty())

    def _save(self) -> None:
        try:
            text = self.editor.toPlainText()
            if text == self._bundled:
                self.store.reset()
            else:
                self.store.save(text)
            self._saved = text
            self._update_status()
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    def _reset(self) -> None:
        answer = QMessageBox.question(
            self,
            "Reset firmware source?",
            "Replace your saved source with the bundled version?",
            QMessageBox.StandardButton.Reset | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Reset:
            return
        try:
            self.store.reset()
            self._saved = self._bundled
            self.editor.setPlainText(self._bundled)
            self._update_status()
        except OSError as exc:
            QMessageBox.critical(self, "Reset failed", str(exc))

    def _export(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Export ProgramPic sketch")
        if not folder:
            return
        destination = Path(folder) / "ProgramPic" / "ProgramPic.ino"
        try:
            self.store.export(self.editor.toPlainText(), destination)
            QMessageBox.information(self, "Sketch exported", f"Saved to:\n{destination}")
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def _close(self) -> None:
        if self._is_dirty():
            answer = QMessageBox.question(
                self,
                "Unsaved changes",
                "Save changes before closing?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if answer == QMessageBox.StandardButton.Save:
                self._save()
                if self._is_dirty():
                    return
            elif answer == QMessageBox.StandardButton.Cancel:
                return
        self.accept()

    def reject(self) -> None:
        if self._is_dirty():
            self._close()
            return
        super().reject()
