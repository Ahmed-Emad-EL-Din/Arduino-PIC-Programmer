"""Small, branded startup window shown while the desktop UI initializes."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)


class StartupSplash(QWidget):
    """A brief centered splash with a crisp logo and a soft gradient reveal."""

    GRADIENT_FADE_IN_MS = 520
    FADE_OUT_MS = 220
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

        # Keep the startup mark outside the animated background layer: the logo
        # and attribution are full-strength from the very first painted frame.
        stack = QStackedLayout(self)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        base = QFrame(self)
        base.setObjectName("splashBase")
        base.setStyleSheet(
            "QFrame#splashBase { background-color: #08172b; "
            "border: 1px solid rgba(54, 207, 226, 90); border-radius: 18px; }"
        )
        stack.addWidget(base)

        gradient = QFrame(self)
        gradient.setObjectName("splashGradient")
        gradient.setStyleSheet(
            "QFrame#splashGradient {"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            "stop:0 #08172b, stop:0.48 #0b2037, stop:1 #102943);"
            "border: 1px solid rgba(54, 207, 226, 90);"
            "border-radius: 18px;"
            "}"
        )
        self._gradient_opacity = QGraphicsOpacityEffect(gradient)
        self._gradient_opacity.setOpacity(0.0)
        gradient.setGraphicsEffect(self._gradient_opacity)
        stack.addWidget(gradient)

        content = QWidget(self)
        content.setObjectName("splashContent")
        content.setStyleSheet("QWidget#splashContent { background: transparent; }")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(26, 30, 26, 28)
        content_layout.setSpacing(12)
        content_layout.addStretch(1)

        logo = QLabel(content)
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
        content_layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignCenter)

        credit = QLabel("Made By: Ahmed Emad", content)
        credit.setObjectName("splashCredit")
        credit.setAccessibleName("Made By: Ahmed Emad")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credit.setStyleSheet(
            "color: #aabbd0; background: transparent; border: none; "
            "font-size: 11px; font-weight: 500; letter-spacing: 0.3px;"
        )
        credit_row = QHBoxLayout()
        credit_row.addStretch(1)
        credit_row.addWidget(credit)
        credit_row.addStretch(1)
        content_layout.addLayout(credit_row)
        content_layout.addStretch(1)
        stack.addWidget(content)
        # In StackAll the current widget is painted above the other layers.
        # Keep the logo/text on top of both background surfaces.
        stack.setCurrentWidget(content)

        self._gradient_animation: Optional[QPropertyAnimation] = None
        self._fade_animation: Optional[QPropertyAnimation] = None

    def show_centered(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            self.move(
                available.x() + (available.width() - self.width()) // 2,
                available.y() + (available.height() - self.height()) // 2,
            )
        # Do not fade the top-level window here: that would make the logo look
        # washed out. Only the background gradient is animated in.
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        animation = QPropertyAnimation(self._gradient_opacity, b"opacity", self)
        animation.setDuration(self.GRADIENT_FADE_IN_MS)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start()
        self._gradient_animation = animation

    def fade_out(self, on_finished: Optional[Callable[[], None]] = None) -> None:
        animation = QPropertyAnimation(self, b"windowOpacity", self)
        animation.setDuration(self.FADE_OUT_MS)
        animation.setStartValue(self.windowOpacity())
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        if on_finished is not None:
            animation.finished.connect(on_finished)
        animation.start()
        self._fade_animation = animation


__all__ = ["StartupSplash"]
