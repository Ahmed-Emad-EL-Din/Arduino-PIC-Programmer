"""Qt worker thread and single-operation lane for blocking hardware tools."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    progressed = Signal(str)
    percented = Signal(int, int)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable, name: str = "Operation", parent=None) -> None:
        super().__init__(parent)
        self.fn = fn
        self.name = name
        self._cancel_requested = False
        self.result = None
        self.error = ""

    def request_cancel(self) -> None:
        # Cancellation is cooperative. A live serial backend must be allowed to
        # close normally so its host process can issue its power-off command.
        self._cancel_requested = True

    def run(self) -> None:
        try:
            self.result = self.fn(self.progressed.emit, self.percented.emit,
                                  lambda: self._cancel_requested)
        except Exception as exc:
            self.error = str(exc)
            self.failed.emit(self.error)
        else:
            self.succeeded.emit(self.result)


class SingleLane:
    def __init__(self) -> None:
        self.current: Optional[Worker] = None

    @property
    def busy(self) -> bool:
        return self.current is not None and self.current.isRunning()

    def start(self, worker: Worker) -> None:
        if self.busy:
            raise RuntimeError("A hardware operation is already running")
        self.current = worker
        worker.finished.connect(self._finished)
        worker.start()

    def _finished(self) -> None:
        current = self.current
        self.current = None
        if current is not None:
            current.deleteLater()

    def cancel(self) -> None:
        if self.current is not None:
            self.current.request_cancel()
