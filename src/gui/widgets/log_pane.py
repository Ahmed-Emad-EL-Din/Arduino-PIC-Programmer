"""Timestamped, filterable, theme-aware activity log widget."""
from __future__ import annotations

import html
from datetime import datetime
from typing import List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


_DARK_LEVELS = {
    "INFO": "#94a0b8",
    "OK": "#10b981",
    "WARN": "#f59e0b",
    "ERR": "#ef4444",
    "TX": "#3b82f6",
    "RX": "#a78bfa",
}

_LIGHT_LEVELS = {
    "INFO": "#475569",
    "OK": "#059669",
    "WARN": "#d97706",
    "ERR": "#dc2626",
    "TX": "#2563eb",
    "RX": "#7c3aed",
}

_HIGH_CONTRAST_LEVELS = {
    "INFO": "#ffffff",
    "OK": "#00ff00",
    "WARN": "#ffff00",
    "ERR": "#ff6b6b",
    "TX": "#00ffff",
    "RX": "#ff80ff",
}


class LogPane(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("logPane")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._theme: str = "dark"
        self._entries: List[Tuple[str, str, str]] = []  # (ts, level, msg)

        self._view = QPlainTextEdit(self)
        self._view.setObjectName("log")
        self._view.setAccessibleName("Activity log messages")
        self._view.setReadOnly(True)
        self._view.setMaximumBlockCount(5000)
        font = QFont("DejaVu Sans Mono")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(9)
        self._view.setFont(font)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(6)
        title = QLabel("Session log")
        title.setObjectName("sectionLabel")
        head.addWidget(title)
        head.addStretch()

        self._filter = QComboBox()
        self._filter.setAccessibleName("Filter activity log")
        self._filter.addItem("All messages", "ALL")
        self._filter.addItem("Warnings & errors", "WARN_ERR")
        self._filter.addItem("Errors only", "ERR")
        self._filter.setMinimumHeight(28)
        self._filter.currentIndexChanged.connect(self._rerender)
        head.addWidget(self._filter)

        copy = QPushButton("Copy")
        copy.setAccessibleName("Copy all activity log messages")
        copy.setFixedHeight(26)
        copy.clicked.connect(self._copy_all)
        clear = QPushButton("Clear")
        clear.setAccessibleName("Clear activity log")
        clear.setFixedHeight(26)
        clear.clicked.connect(self._clear_all)
        save = QPushButton("Export…")
        save.setAccessibleName("Export activity log")
        save.setFixedHeight(26)
        save.clicked.connect(self._save)
        for b in (copy, clear, save):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            head.addWidget(b)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 8)
        lay.setSpacing(4)
        lay.addLayout(head)
        lay.addWidget(self._view, 1)

    def set_theme(self, theme: str) -> None:
        if theme != self._theme:
            self._theme = theme
            self._rerender()

    def log(self, msg: str, level: str = "INFO") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        lvl = level.upper()
        self._entries.append((ts, lvl, msg))
        if len(self._entries) > 4000:
            self._entries = self._entries[-3000:]
        if self._matches_filter(lvl):
            self._append_formatted(ts, lvl, msg)

    def _matches_filter(self, lvl: str) -> bool:
        mode = self._filter.currentData()
        if mode == "WARN_ERR":
            return lvl in ("WARN", "ERR")
        if mode == "ERR":
            return lvl == "ERR"
        return True

    def _append_formatted(self, ts: str, lvl: str, msg: str) -> None:
        if self._theme == "high_contrast":
            levels = _HIGH_CONTRAST_LEVELS
            ts_col = body_col = "#ffffff"
        elif self._theme == "light":
            levels = _LIGHT_LEVELS
            ts_col, body_col = "#64748b", "#0f172a"
        else:
            levels = _DARK_LEVELS
            ts_col, body_col = "#94a0b8", "#dbe2ef"
        color = levels.get(lvl, levels["INFO"])
        safe = html.escape(msg).replace("\n", "<br>")
        self._view.appendHtml(
            f'<span style="color:{ts_col}">{ts}</span> '
            f'<span style="color:{color};font-weight:700">[{lvl}]</span> '
            f'<span style="color:{body_col}">{safe}</span>'
        )
        self._view.moveCursor(QTextCursor.MoveOperation.End)

    def _rerender(self) -> None:
        self._view.clear()
        for ts, lvl, msg in self._entries:
            if self._matches_filter(lvl):
                self._append_formatted(ts, lvl, msg)

    def _clear_all(self) -> None:
        self._entries.clear()
        self._view.clear()

    def text(self) -> str:
        return "\n".join(f"{ts} [{lvl}] {msg}" for ts, lvl, msg in self._entries)

    def _copy_all(self) -> None:
        self._view.selectAll()
        self._view.copy()
        self._view.moveCursor(QTextCursor.MoveOperation.End)

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Activity Log",
            "arduino-pic-programmer-log.txt",
            "Text files (*.txt);;All files (*)",
        )
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.text() + "\n")
