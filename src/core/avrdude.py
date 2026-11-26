"""Arduino board metadata and safe avrdude firmware-upload helper."""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


class FlashError(RuntimeError):
    """Arduino firmware upload failed or required build assets are missing."""


@dataclass(frozen=True)
class Board:
    key: str
    label: str
    mcu: str
    avrdude_part: str
    bootloader_baud: int
    reset_cap_note: str = ""
    firmware_flash_supported: bool = True


BOARDS: List[Board] = [
    Board("uno", "Arduino Uno", "ATmega328P", "m328p", 115200),
    Board("nano_new", "Arduino Nano (new bootloader)", "ATmega328P", "m328p", 115200),
    Board("nano_old", "Arduino Nano (old bootloader)", "ATmega328P", "m328p", 57600),
    Board("pro_mini_5v", "Arduino Pro Mini (5 V / 16 MHz)", "ATmega328P", "m328p", 57600,
          "Use only the 5 V / 16 MHz variant. A 3.3 V Pro Mini is not compatible with this 5 V PIC circuit."),
    Board("mega2560", "Arduino Mega 2560", "ATmega2560", "m2560", 115200),
    Board("leonardo", "Arduino Leonardo", "ATmega32U4", "m32u4", 57600,
          firmware_flash_supported=False),
    Board("micro", "Arduino Micro", "ATmega32U4", "m32u4", 57600,
          firmware_flash_supported=False),
]
BOARD_BY_KEY: Dict[str, Board] = {b.key: b for b in BOARDS}


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[2]


def find_avrdude() -> Optional[Path]:
    override = os.environ.get("ARDPICPROG_AVRDUDE")
    candidates = [Path(override)] if override else []
    root = _resource_root()
    candidates += [root / "tools" / "avrdude" / "avrdude.exe",
                   root / "tools" / "avrdude" / "avrdude",
                   root / "tools" / "avrdude.exe", root / "tools" / "avrdude"]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    from shutil import which
    found = which("avrdude") or which("avrdude.exe")
    return Path(found) if found else None


def firmware_hex(board_key: str) -> Path:
    path = _resource_root() / "firmware" / "precompiled" / f"{board_key}.hex"
    if not path.is_file():
        raise FlashError(
            f"Precompiled ProgramPic firmware for {board_key} is not included in this build. "
            "Rebuild the firmware package before using Flash Arduino."
        )
    return path


def flash_firmware(board_key: str, port: str) -> str:
    board = BOARD_BY_KEY.get(board_key)
    if board is None:
        raise FlashError(f"Unsupported Arduino board: {board_key}")
    if not board.firmware_flash_supported:
        raise FlashError(
            f"Firmware upload for {board.label} needs a bootloader-port reset flow that is not implemented yet. "
            "Upload ProgramPic from Arduino IDE instead; the PIC programming connection can still use the board once firmware is installed."
        )
    if not port:
        raise FlashError("Select a serial port before flashing firmware.")
    avrdude = find_avrdude()
    if avrdude is None:
        raise FlashError("avrdude was not found. It must be bundled or installed on PATH.")
    image = firmware_hex(board_key)
    root = _resource_root()
    conf_candidates = [root / "tools" / "avrdude" / "avrdude.conf",
                       root / "tools" / "avrdude.conf", avrdude.parent / "avrdude.conf"]
    conf = next((p for p in conf_candidates if p.is_file()), None)
    if conf is None:
        raise FlashError("avrdude.conf is missing from the application package.")

    command = [str(avrdude), "-C", str(conf), "-v", "-p", board.avrdude_part,
               "-c", "arduino", "-P", port, "-b", str(board.bootloader_baud),
               "-D", "-U", f"flash:w:{image}:i"]
    try:
        launch_options = {}
        if os.name == "nt":
            launch_options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
            **launch_options,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FlashError(f"Could not run avrdude: {exc}") from exc
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if result.returncode:
        raise FlashError(output or f"avrdude exited with status {result.returncode}")
    return output or f"ProgramPic firmware uploaded to {board.label} on {port}."
