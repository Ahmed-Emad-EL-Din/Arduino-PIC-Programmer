"""Small, branded startup window shown while the desktop UI initializes."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class StartupSplash(QWidget):
    """A brief centered splash with a restrained fade transition."""

    FADE_IN_MS = 220
    FADE_OUT_MS = 240
    WIDTH = 390
    HEIGHT = 365
    LOGO_SIZE = 230

    def __init__(self, logo_path: Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("startupSplash")
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setAccessibleName("Arduino-PIC Programmer startup")
        self.setAccessibleDescription("Application is starting")

        card = QFrame(self)
        card.setObjectName("splashCard")
        card.setStyleSheet(
            "QFrame#splashCard {"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            "stop:0 #08172b, stop:1 #102943);"
            "border: 1px solid rgba(54, 207, 226, 90);"
            "border-radius: 18px;"
            "}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(12)

        logo = QLabel(card)
        logo.setObjectName("splashLogo")
        logo.setAccessibleName("Arduino-PIC Programmer logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(str(logo_path))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(
                self.LOGO_SIZE,
                self.LOGO_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        else:
            logo.setText("Arduino-PIC Programmer")
            logo.setStyleSheet("color: #eef6ff; font-size: 17px; font-weight: 600;")
        layout.addStretch(1)
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignCenter)

        credit = QLabel("Made By: Ahmed Emad", card)
        credit.setObjectName("splashCredit")
        credit.setAccessibleName("Made By: Ahmed Emad")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credit.setStyleSheet(
            "color: #aabbd0; background: transparent; border: none; "
            "font-size: 11px; font-weight: 500; letter-spacing: 0.3px;"
        )
        layout.addWidget(credit, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

        self._fade_animation: Optional[QPropertyAnimation] = None

    def show_centered(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            self.move(
                available.x() + (available.width() - self.width()) // 2,
                available.y() + (available.height() - self.height()) // 2,
            )
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._animate_opacity(1.0, self.FADE_IN_MS)

    def fade_out(self, on_finished: Optional[Callable[[], None]] = None) -> None:
        animation = self._animate_opacity(0.0, self.FADE_OUT_MS)
        if on_finished is not None:
            animation.finished.connect(on_finished)

    def _animate_opacity(self, target: float, duration_ms: int) -> QPropertyAnimation:
        animation = QPropertyAnimation(self, b"windowOpacity", self)
        animation.setDuration(duration_ms)
        animation.setStartValue(self.windowOpacity())
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        animation.start()
        self._fade_animation = animation
        return animation


__all__ = ["StartupSplash"]
