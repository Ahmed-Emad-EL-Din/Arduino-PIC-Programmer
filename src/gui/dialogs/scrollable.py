"""Helpers for dialogs that remain usable on short displays."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QScrollArea, QWidget


def scrollable_content(content: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setObjectName("dialogContentScroll")
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setWidget(content)
    return area


def fit_dialog_to_screen(
    dialog: QDialog,
    preferred_width: int,
    preferred_height: int,
    minimum_width: int = 360,
    minimum_height: int = 280,
) -> None:
    """Use the available work area, leaving content to scroll when needed."""
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        dialog.resize(preferred_width, preferred_height)
        return
    available = screen.availableGeometry()
    max_width = max(320, int(available.width() * 0.94))
    max_height = max(240, int(available.height() * 0.92))
    dialog.setMaximumSize(max_width, max_height)
    dialog.setMinimumSize(min(minimum_width, max_width), min(minimum_height, max_height))
    dialog.resize(min(preferred_width, max_width), min(preferred_height, max_height))


__all__ = ["fit_dialog_to_screen", "scrollable_content"]
