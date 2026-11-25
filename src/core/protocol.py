"""Data types and errors shared by the host-programmer backend."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


class ProtocolError(RuntimeError):
    """The programmer returned an invalid or unsuccessful response."""


class ProgrammerNotReady(ProtocolError):
    """No compatible ProgramPic host programmer is connected."""


@dataclass(frozen=True)
class DeviceInfo:
    device_id: Optional[int] = None
    config_word: Optional[int] = None
    device_name: str = ""


@dataclass
class ProgrammerState:
    port: str = ""
    firmware: str = ""
    verified: bool = False
    supported: List[str] = field(default_factory=list)
