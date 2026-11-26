"""Serial-port discovery and serial-related backend exceptions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


class LinkError(RuntimeError):
    """Serial communication failed."""


class LinkTimeout(LinkError):
    """The programmer did not respond before the configured timeout."""


@dataclass(frozen=True)
class SerialPortInfo:
    device: str
    description: str
    hwid: str = ""

    @property
    def is_likely_arduino(self) -> bool:
        text = f"{self.description} {self.hwid}".casefold()
        known_wch_vid = "vid:pid=1a86:" in text or "vid_1a86&pid_" in text
        return known_wch_vid or any(
            token in text for token in ("arduino", "ch340", "wchusb", "usb serial")
        )

    def label(self) -> str:
        return f"{self.device} — {self.description}" if self.description else self.device

    def __str__(self) -> str:
        return self.label()


def list_serial_ports() -> List[SerialPortInfo]:
    """Return ports using pyserial's cross-platform discovery API."""
    try:
        from serial.tools import list_ports
    except ImportError as exc:
        raise LinkError("pyserial is required for serial-port discovery") from exc
    ports = []
    for port in list_ports.comports():
        ports.append(SerialPortInfo(port.device, port.description or "", port.hwid or ""))
    return sorted(ports, key=lambda p: p.device.casefold())
