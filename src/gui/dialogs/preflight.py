"""Mandatory user-confirmed hardware preflight and destructive-action prompts."""
from __future__ import annotations

from typing import List, Optional
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QLabel,
                               QMessageBox, QScrollArea, QVBoxLayout, QWidget)
from core.safety import PreflightItem, build_dynamic_preflight
from core.mcu_db import DEFAULT_DEVICE


class PreflightDialog(QDialog):
    def __init__(self, items: List[PreflightItem], title: str = "Hardware preflight",
                 subtitle: str = "Verify every item before continuing.", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(680, 560)
        layout = QVBoxLayout(self)
        intro = QLabel(subtitle + "\n\nProgramming voltages can permanently damage a chip or board.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        self.checks = []
        for item in items:
            check = QCheckBox(item.text)
            check.setProperty("critical", item.critical)
            check.stateChanged.connect(self._sync)
            body_layout.addWidget(check)
            self.checks.append(check)
        body_layout.addStretch()
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.continue_button = self.buttons.addButton("I verified — Continue", QDialogButtonBox.ButtonRole.AcceptRole)
        self.continue_button.setEnabled(False)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.accept)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)
        layout.addWidget(self.buttons)

    def _sync(self, *_args) -> None:
        self.continue_button.setEnabled(all(c.isChecked() for c in self.checks if c.property("critical")))


def show_preflight(parent, seen: bool, dev=DEFAULT_DEVICE, board_key: str = "uno") -> bool:
    items = build_dynamic_preflight(dev, board_key)
    title = "Confirm hardware preflight" if not seen else "Re-confirm hardware wiring"
    subtitle = f"Selected target: {dev.display_name}. Confirm the physical setup for this board and target."
    dialog = PreflightDialog(items, title, subtitle, parent)
    return dialog.exec() == QDialog.DialogCode.Accepted


def confirm_erase(parent, dev) -> bool:
    answer = QMessageBox.warning(
        parent, f"Erase {dev.display_name}?",
        "This permanently erases user memory on the selected PIC. Factory calibration is preserved by the host firmware. Continue only after confirming the target and wiring.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Cancel,
    )
    return answer == QMessageBox.StandardButton.Yes


def confirm_program(parent, dev, filename: str, summary: str, do_verify: bool) -> bool:
    verification = "Read-back verification is enabled." if do_verify else "WARNING: read-back verification is disabled."
    answer = QMessageBox.warning(
        parent, f"Program {dev.display_name}?",
        f"File: {filename}\n\n{summary}\n\n{verification}\n\nThe host will erase, write, and then power off the socket. Continue?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Cancel,
    )
    return answer == QMessageBox.StandardButton.Yes
