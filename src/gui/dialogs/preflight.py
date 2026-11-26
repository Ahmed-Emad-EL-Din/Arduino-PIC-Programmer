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
        self.cancel_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        self.cancel_button.setDefault(True)
        self.cancel_button.setAutoDefault(True)
        self.cancel_button.setFocus()
        self.continue_button.setAutoDefault(False)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.buttons)

    def _sync(self, *_args) -> None:
        self.continue_button.setEnabled(all(c.isChecked() for c in self.checks if c.property("critical")))


def show_preflight(parent, seen: bool, dev=DEFAULT_DEVICE, board_key: str = "uno") -> bool:
    items = build_dynamic_preflight(dev, board_key)
    title = "Confirm hardware preflight" if not seen else "Re-confirm hardware wiring"
    subtitle = f"Selected target: {dev.display_name}. Confirm the physical setup for this board and target."
    dialog = PreflightDialog(items, title, subtitle, parent)
    return dialog.exec() == QDialog.DialogCode.Accepted


def confirm_erase(parent, dev, preserve_calibration: bool = True) -> bool:
    if not preserve_calibration:
        QMessageBox.warning(
            parent,
            "Erase blocked",
            "This build cannot erase with calibration preservation disabled unless an explicit factory-calibration backup is supplied. Keep preservation enabled; no erase command was sent.",
        )
        return False
    answer = QMessageBox.warning(
        parent,
        f"Erase {dev.display_name}?",
        "This permanently erases user memory on the selected PIC. Calibration preservation is requested, but host behavior has not been hardware-validated for every device. The host uses the selected device map; raw silicon ID is not exposed to this app. Socket voltage is not measured. Confirm the package marking, wiring, and external VPP supply; verify VPP is off before touching the target.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Cancel,
    )
    return answer == QMessageBox.StandardButton.Yes


def confirm_program(parent, dev, filename: str, summary: str, do_verify: bool) -> bool:
    verification = "Read-back comparison is enabled." if do_verify else "WARNING: read-back comparison is disabled."
    answer = QMessageBox.warning(
        parent, f"Program {dev.display_name}?",
        f"File: {filename}\n\n{summary}\n\n{verification}\n\nContinue only after confirming the chip marking and wiring. The app cannot measure socket voltage; verify the external VPP supply is off before touching the target.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Cancel,
    )
    return answer == QMessageBox.StandardButton.Yes
