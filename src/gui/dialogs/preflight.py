"""Mandatory user-confirmed hardware preflight and destructive-action prompts."""
from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.mcu_db import DEFAULT_DEVICE
from core.safety import PreflightItem, build_dynamic_preflight
from .scrollable import fit_dialog_to_screen


class _CheckLabel(QLabel):
    """Wrapped checklist text that remains clickable like a checkbox label."""

    def __init__(self, text: str, checkbox: QCheckBox, parent=None) -> None:
        super().__init__(text, parent)
        self._checkbox = checkbox
        self.setBuddy(checkbox)
        self.setWordWrap(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(text)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._checkbox.setChecked(not self._checkbox.isChecked())
            event.accept()
            return
        super().mouseReleaseEvent(event)


class PreflightDialog(QDialog):
    def __init__(
        self,
        items: List[PreflightItem],
        title: str = "Hardware preflight",
        subtitle: str = "Verify every item before continuing.",
        parent=None,
        previously_checked: bool = False,
        age_minutes: int = 0,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setSizeGripEnabled(True)

        layout = QVBoxLayout(self)
        recent_note = (
            f"\nA complete check was confirmed {age_minutes} minute(s) ago. "
            "The boxes are carried forward for this board and target; if anything changed, clear them and re-check."
            if previously_checked else ""
        )
        intro = QLabel(
            subtitle + recent_note + "\n\nPhysically inspect the setup before marking items. "
            "These checks are user confirmations, not electrical measurements. Cancel sends no command."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("preflightChecklistScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(8, 8, 12, 8)
        body_layout.setSpacing(10)
        self.checks: list[QCheckBox] = []
        self.check_labels: list[QLabel] = []
        for item in items:
            row = QWidget(body)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)
            check = QCheckBox(row)
            check.setObjectName("preflightCheckBox")
            check.setProperty("critical", item.critical)
            check.setAccessibleName(item.text)
            check.setAccessibleDescription("Required physical hardware confirmation")
            label = _CheckLabel(item.text, check, row)
            row_layout.addWidget(check, 0, Qt.AlignmentFlag.AlignTop)
            row_layout.addWidget(label, 1)
            check.toggled.connect(self._sync)
            body_layout.addWidget(row)
            self.checks.append(check)
            self.check_labels.append(label)
        body_layout.addStretch()
        self.scroll.setWidget(body)
        layout.addWidget(self.scroll, 1)

        bulk_row = QHBoxLayout()
        self.check_all_button = QPushButton("Check all items")
        self.check_all_button.setObjectName("checkAllPreflight")
        self.check_all_button.setAccessibleName("Mark all physical preflight items checked")
        self.check_all_button.setToolTip(
            "Use only after you have physically inspected every listed wiring and safety item."
        )
        self.clear_all_button = QPushButton("Clear all")
        self.clear_all_button.setAccessibleName("Clear all preflight checks")
        self.check_all_button.clicked.connect(lambda: self._set_all(True))
        self.clear_all_button.clicked.connect(lambda: self._set_all(False))
        bulk_row.addWidget(self.check_all_button)
        bulk_row.addWidget(self.clear_all_button)
        bulk_row.addStretch(1)
        layout.addLayout(bulk_row)

        self.check_summary = QLabel()
        self.check_summary.setWordWrap(True)
        self.check_summary.setObjectName("preflightProgress")
        layout.addWidget(self.check_summary)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.continue_button = self.buttons.addButton(
            "Continue", QDialogButtonBox.ButtonRole.AcceptRole
        )
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

        if previously_checked:
            self._set_all(True)
        else:
            self._sync()
        fit_dialog_to_screen(self, 780, 620, 520, 390)

    def _set_all(self, checked: bool) -> None:
        for checkbox in self.checks:
            checkbox.setChecked(checked)
        self._sync()

    def _sync(self, *_args) -> None:
        required = [check for check in self.checks if check.property("critical")]
        checked = sum(check.isChecked() for check in required)
        self.continue_button.setEnabled(bool(required) and checked == len(required))
        self.check_summary.setText(f"{checked} of {len(required)} required checks")


def show_preflight(
    parent,
    seen: bool,
    dev=DEFAULT_DEVICE,
    board_key: str = "uno",
    age_minutes: int = 0,
    expired: bool = False,
) -> bool:
    items = build_dynamic_preflight(dev, board_key)
    title = (
        "Re-check hardware preflight" if expired else
        "Confirm hardware preflight" if not seen else "Re-confirm hardware wiring"
    )
    subtitle = f"Selected target: {dev.display_name}. Confirm the physical setup for this board and target."
    if expired:
        subtitle += " The previous check expired; all items must be reviewed again."
    dialog = PreflightDialog(
        items, title, subtitle, parent,
        previously_checked=seen and not expired,
        age_minutes=age_minutes,
    )
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
