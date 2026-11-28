"""Application entry point."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT, ROOT / "src"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from PySide6.QtCore import QElapsedTimer, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from app import APP_NAME, ORG_NAME
from app.diagnostics import configure_logging, install_exception_hooks
from gui.main_window import MainWindow
from gui.startup_splash import StartupSplash


# A short minimum keeps the requested mark visible long enough to register;
# startup work happens concurrently and the splash never adds a long wait.
MIN_SPLASH_MS = 620


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    configure_logging()
    install_exception_hooks()
    app_root = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else ROOT
    icon_path = app_root / "assets" / "app-icon.ico"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    splash = StartupSplash(app_root / "assets" / "app-icon.png")
    splash_clock = QElapsedTimer()
    splash_clock.start()
    splash.show_centered()
    # Flush the first paint before constructing the heavier main window.
    app.processEvents()
    window_holder = []

    def open_main_window() -> None:
        window = MainWindow()
        if icon_path.is_file():
            window.setWindowIcon(QIcon(str(icon_path)))
        window_holder.append(window)
        window.show()

        wait_ms = max(0, MIN_SPLASH_MS - splash_clock.elapsed())
        QTimer.singleShot(wait_ms, lambda: splash.fade_out(splash.close))

    # Let the fade-in begin and the splash paint before UI setup starts.
    QTimer.singleShot(90, open_main_window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
