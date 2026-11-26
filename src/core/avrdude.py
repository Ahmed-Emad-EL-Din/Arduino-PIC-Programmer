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
    alternate_bootloader_baud: Optional[int] = None


@dataclass(frozen=True)
class FlashResult:
    output: str
    board_key: str
    baud: int
    fallback_used: bool = False


BOARDS: List[Board] = [
    Board("uno", "Arduino Uno", "ATmega328P", "m328p", 115200),
    Board("nano_new", "Arduino Nano (new bootloader)", "ATmega328P", "m328p", 115200,
          alternate_bootloader_baud=57600),
    Board("nano_old", "Arduino Nano (old bootloader)", "ATmega328P", "m328p", 57600,
          alternate_bootloader_baud=115200),
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


def _run_avrdude(command: list[str]) -> subprocess.CompletedProcess:
    launch_options = {}
    if os.name == "nt":
        launch_options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        return subprocess.run(
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


def _avrdude_output(result: subprocess.CompletedProcess) -> str:
    return "\n".join(part for part in (result.stdout, result.stderr) if part).strip()


def _is_bootloader_sync_error(output: str) -> bool:
    lowered = output.casefold()
    return any(
        marker in lowered
        for marker in ("not in sync", "stk500_getsync", "programmer is not responding")
    )


def _command(avrdude: Path, conf: Path, image: Path, board: Board,
             port: str, baud: int) -> list[str]:
    return [
        str(avrdude), "-C", str(conf), "-v", "-p", board.avrdude_part,
        "-c", "arduino", "-P", port, "-b", str(baud),
        "-D", "-U", f"flash:w:{image}:i",
    ]


def flash_firmware(board_key: str, port: str) -> FlashResult:
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

    result = _run_avrdude(
        _command(avrdude, conf, image, board, port, board.bootloader_baud)
    )
    output = _avrdude_output(result)
    if result.returncode == 0:
        return FlashResult(
            output or f"ProgramPic firmware uploaded to {board.label} on {port}.",
            board.key,
            board.bootloader_baud,
        )

    alternate_baud = board.alternate_bootloader_baud
    if alternate_baud is None or not _is_bootloader_sync_error(output):
        raise FlashError(output or f"avrdude exited with status {result.returncode}")

    try:
        retry = _run_avrdude(
            _command(avrdude, conf, image, board, port, alternate_baud)
        )
    except FlashError as exc:
        raise FlashError(
            f"Nano bootloader did not synchronize at {board.bootloader_baud} baud, and the "
            f"automatic retry at {alternate_baud} baud could not complete.\n\n"
            f"First attempt:\n{output}\n\nRetry error:\n{exc}"
        ) from exc

    retry_output = _avrdude_output(retry)
    if retry.returncode == 0:
        actual_board_key = (
            "nano_new" if alternate_baud == 115200 else "nano_old"
        ) if board.key in ("nano_new", "nano_old") else board.key
        actual_board = BOARD_BY_KEY[actual_board_key]
        return FlashResult(
            f"Initial attempt at {board.bootloader_baud} baud did not synchronize. "
            f"Upload succeeded using the alternate {alternate_baud}-baud Nano bootloader "
            f"setting; the app will remember {actual_board.label}.\n\n{retry_output}",
            actual_board_key,
            alternate_baud,
            fallback_used=True,
        )

    raise FlashError(
        f"Nano upload failed at both supported bootloader speeds "
        f"({board.bootloader_baud} and {alternate_baud} baud).\n\n"
        "Check that the selected COM port belongs to the Nano and is not open in another "
        "serial tool. The app tried both standard Nano bootloaders. If both attempts report "
        "not-in-sync, press Reset just before retrying and check that the board's reset/auto-reset "
        "circuit is not held down.\n\n"
        f"Attempt at {board.bootloader_baud} baud:\n{output}\n\n"
        f"Attempt at {alternate_baud} baud:\n{retry_output}"
    )
