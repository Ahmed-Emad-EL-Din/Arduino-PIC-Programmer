"""Persistent diagnostics for failures in the desktop application."""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
import threading
import uuid
from pathlib import Path
from types import TracebackType

from app import ORG_NAME

_LOG = logging.getLogger("ardpicprog")
_LOG_FILE: Path | None = None


def _default_log_directory() -> Path:
    try:
        from PySide6.QtCore import QStandardPaths

        location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
        if location:
            return Path(location) / "logs"
    except Exception:
        pass

    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Logs"
    else:
        base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    return base / ORG_NAME / "logs"


def configure_logging(log_directory: Path | None = None) -> Path:
    """Set up a small rotating log and return its full path."""
    global _LOG_FILE
    if _LOG_FILE is not None:
        return _LOG_FILE

    directory = log_directory or _default_log_directory()
    log_path = directory / "application.log"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s"
        ))
        _LOG.addHandler(handler)
        _LOG.setLevel(logging.INFO)
        _LOG.propagate = False
        _LOG_FILE = log_path
    except Exception:
        # Keep the GUI usable even when the profile directory is read-only.
        _LOG_FILE = None
    return log_path


def log_path() -> Path:
    return _LOG_FILE or (_default_log_directory() / "application.log")


def report_exception(context: str, exc: BaseException) -> str:
    """Log a full traceback and return a concise message suitable for the UI."""
    configure_logging()
    diagnostic_id = uuid.uuid4().hex[:8].upper()
    exc_info: tuple[type[BaseException], BaseException, TracebackType | None] = (
        type(exc), exc, exc.__traceback__
    )
    _LOG.error(
        "[%s] %s failed: %s: %s",
        diagnostic_id,
        context,
        type(exc).__name__,
        exc,
        exc_info=exc_info,
    )
    detail = str(exc).strip() or "No additional error text was provided."
    destination = str(_LOG_FILE) if _LOG_FILE else "unavailable (the profile log folder is not writable)"
    return (
        f"{context} failed ({type(exc).__name__}): {detail}\n"
        f"Diagnostic ID: {diagnostic_id}\n"
        f"Full log: {destination}"
    )


def show_diagnostic_error(parent, title: str, message: str, *, critical: bool = False) -> None:
    """Show a copyable diagnostic message without hiding the full error text."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QMessageBox

    box = QMessageBox(parent)
    box.setIcon(
        QMessageBox.Icon.Critical if critical else QMessageBox.Icon.Warning
    )
    box.setWindowTitle(title)
    box.setText(message)
    box.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
        | Qt.TextInteractionFlag.TextSelectableByKeyboard
    )
    copy = box.addButton("Copy details", QMessageBox.ButtonRole.ActionRole)
    copy.clicked.connect(lambda: QApplication.clipboard().setText(message))
    box.addButton(QMessageBox.StandardButton.Ok)
    box.exec()


def install_exception_hooks() -> None:
    """Log uncaught main-thread and Python-thread exceptions with tracebacks."""
    def main_hook(exc_type, exc, tb):
        exc.__traceback__ = tb
        message = report_exception("Unexpected application error", exc)
        try:
            from PySide6.QtWidgets import QApplication

            if QApplication.instance() is not None:
                show_diagnostic_error(
                    None, "Unexpected application error", message, critical=True
                )
        except Exception:
            pass

    def thread_hook(args: threading.ExceptHookArgs):
        context = f"Uncaught exception in thread {args.thread.name if args.thread else 'unknown'}"
        _LOG.critical(context, exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    sys.excepthook = main_hook
    threading.excepthook = thread_hook
