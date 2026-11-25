"""Small programmatic icons; no external icon pack is required at runtime."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


def icon(name: str, color: str = "#8aa0b7") -> QIcon:
    pix = QPixmap(24, 24)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin))
    glyphs = {
        "open": "↗", "download": "↓", "circuit": "⌘", "log": "≡", "refresh": "↻",
        "upload": "↑", "plug": "●", "unplug": "○", "chip": "▦", "check": "✓",
        "play": "▶", "shield": "◇", "erase": "×", "theme": "◐", "settings": "⚙",
        "help": "?", "info": "i",
    }
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, glyphs.get(name, "•"))
    painter.end()
    return QIcon(pix)
