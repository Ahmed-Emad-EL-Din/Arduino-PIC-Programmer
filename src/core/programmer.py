"""Safe adapter around the upstream ArdPicProg 1.8.horo host executable.

The executable owns the serial protocol and sends PWROFF when it closes the
port. Each operation runs in a separate process and is followed by a read-back
comparison for writes; the GUI never speaks undocumented serial commands.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional, Sequence, Tuple, Union

from .ihex import HexImage, IHexError
from .mcu_db import McuDevice, find_by_id, lookup
from .protocol import DeviceInfo, ProgrammerNotReady, ProgrammerState, ProtocolError
from .safety import SafetyViolation, gate_hex_fits

Progress = Optional[Callable[[str], None]]
Percent = Optional[Callable[[int, int], None]]


@dataclass
class _RunResult:
    stdout: str
    stderr: str
    returncode: int


class ProgrammerSession:
    def __init__(self, use_binary: bool = True,
                 host_path: Optional[Union[str, Sequence[str]]] = None) -> None:
        self.use_binary = use_binary
        self._host_override = host_path or os.environ.get("ARDPICPROG_HOST")
        self.state = ProgrammerState()
        self._cancel_requested = threading.Event()
        self._active_lock = threading.Lock()
        self._active_process: Optional[subprocess.Popen] = None

    @property
    def connected(self) -> bool:
        return bool(self.state.verified and self.state.port)

    def _root(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return Path(__file__).resolve().parents[2]

    def _host(self) -> str:
        root = self._root()
        candidates = [root / "tools" / "ardpicprog.exe", root / "tools" / "ardpicprog",
                      root / "vendor" / "ArdPicProg" / "ardpicprog.exe",
                      root / "vendor" / "ArdPicProg" / "ardpicprog"]
        for path in candidates:
            if path.is_file():
                return str(path)
        found = shutil.which("ardpicprog.exe") or shutil.which("ardpicprog")
        if found:
            return found
        raise ProgrammerNotReady(
            "The ArdPicProg host executable is missing. Build/package tools/ardpicprog.exe first."
        )

    def _host_command(self, args) -> list[str]:
        override = self._host_override
        if isinstance(override, (list, tuple)):
            return [*map(str, override), *map(str, args)]
        if isinstance(override, str) and override:
            candidate = Path(override)
            resolved = str(candidate) if candidate.is_file() else shutil.which(override)
            if not resolved:
                raise ProgrammerNotReady(f"Configured host executable does not exist: {override}")
            return [resolved, *map(str, args)]
        return [self._host(), *map(str, args)]

    def _run(self, args, progress: Progress = None, timeout: int = 600,
             check_cancel: bool = True) -> _RunResult:
        if check_cancel and self._cancel_requested.is_set():
            self._cancel_requested.clear()
            raise ProtocolError("Operation cancelled before it started; no hardware command was sent.")
        command = self._host_command(args)
        launch_options = {}
        if os.name == "nt":
            launch_options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, encoding="utf-8", errors="replace",
                                       **launch_options)
        except OSError as exc:
            raise ProgrammerNotReady(f"Could not start ArdPicProg host: {exc}") from exc
        with self._active_lock:
            self._active_process = process
        stdout_lines, stderr_lines = [], []

        def drain(stream, sink):
            for line in iter(stream.readline, ""):
                sink.append(line)
                if progress:
                    progress(line.rstrip("\r\n"))

        readers = [
            threading.Thread(target=drain, args=(process.stdout, stdout_lines), daemon=True),
            threading.Thread(target=drain, args=(process.stderr, stderr_lines), daemon=True),
        ]
        for reader in readers:
            reader.start()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            # Do not claim that an interrupted hardware operation is safe. The
            # upstream firmware auto-powers-off on inactivity; the process is
            # terminated only after a long serial timeout has already elapsed.
            process.kill()
            process.wait()
            for reader in readers:
                reader.join(timeout=2)
            stdout, stderr = "".join(stdout_lines), "".join(stderr_lines)
            message = (stderr or stdout).strip()
            raise ProtocolError(
                "ArdPicProg timed out. The child process was stopped; verify the programmer's "
                "safe state before touching the target. " + message
            ) from exc
        finally:
            for reader in readers:
                reader.join(timeout=2)
            with self._active_lock:
                self._active_process = None
            # A cancellation requested during a serial command is deferred until
            # the host process closes the port normally (and sends PWROFF).
            self._cancel_requested.clear()
        return _RunResult("".join(stdout_lines), "".join(stderr_lines), process.returncode)

    @staticmethod
    def _output(result: _RunResult) -> str:
        return "\n".join(s for s in (result.stdout, result.stderr) if s).strip()

    def _checked(self, args, progress: Progress = None, check_cancel: bool = True) -> str:
        result = self._run(args, progress, check_cancel=check_cancel)
        output = self._output(result)
        if result.returncode:
            raise ProtocolError(output or f"ArdPicProg exited with status {result.returncode}")
        return output

    def connect(self, port: str, baud: int = 115200, progress: Progress = None) -> ProgrammerState:
        if not port:
            raise ProgrammerNotReady("Select a serial port first.")
        self._cancel_requested.clear()
        output = self._checked(["--pic-serial-port", port, "--speed", baud, "--list-devices"], progress)
        devices = []
        in_list = False
        for line in output.splitlines():
            text = line.strip()
            if text.casefold().startswith("supported devices:"):
                in_list = True
                continue
            if in_list and text and text != "* = autodetected":
                # Firmware list lines start with a marker such as "*" or a
                # device token. Keep only lowercase PIC identifiers.
                devices.extend(m.lower() for m in re.findall(r"\b(pic\w+)\b", text, re.IGNORECASE))
        self.state = ProgrammerState(port=port, firmware="1.8.horo", verified=True,
                                     supported=sorted(set(devices)))
        return self.state

    def disconnect(self) -> None:
        # Operations own and close their port. Closing the GUI clears the
        # verified-session latch; the C++ host issues PWROFF on each exit.
        self.state = ProgrammerState()
        self._cancel_requested.clear()

    def request_cancel(self) -> None:
        # We do not kill an in-flight serial subprocess: doing so can interrupt
        # a write before it can send PWROFF. This flag prevents the next action.
        self._cancel_requested.set()

    def _require_connected(self) -> str:
        if not self.connected:
            raise ProgrammerNotReady("Connect to a verified ProgramPic programmer first.")
        return self.state.port

    def detect_chip(self, progress: Progress = None) -> Tuple[DeviceInfo, Optional[McuDevice]]:
        port = self._require_connected()
        output = self._checked(["--pic-serial-port", port, "--detect"], progress)
        match = re.search(r"\bDevice\s+(pic[\w]+)\s*,", output, re.IGNORECASE)
        if not match:
            raise ProtocolError("Programmer connected, but no supported device name was returned. "
                                "For chips without an ID, select the exact MCU manually before programming.")
        device = lookup(match.group(1))
        if device is None:
            return DeviceInfo(device_name=match.group(1)), None
        # The upstream CLI verifies the requested/auto-detected device name but
        # does not expose raw ID/config words as structured output. Do not
        # present the database's expected ID as if it were a measured value.
        return DeviceInfo(device_name=device.display_name), device

    @staticmethod
    def _write_temp_hex(image: HexImage) -> Path:
        handle = tempfile.NamedTemporaryFile(prefix="ardpicprog-", suffix=".hex", delete=False)
        path = Path(handle.name)
        try:
            handle.write(image.to_hex().encode("ascii"))
        finally:
            handle.close()
        return path

    def _readback(self, dev: McuDevice, progress: Progress = None,
                  check_cancel: bool = True) -> HexImage:
        port = self._require_connected()
        with tempfile.TemporaryDirectory(prefix="ardpicprog-read-") as directory:
            path = Path(directory) / "readback.hex"
            self._checked(["--pic-serial-port", port, "--device", dev.name,
                           "--output-hexfile", path], progress, check_cancel=check_cancel)
            return HexImage.load(path)

    @staticmethod
    def _compare(expected: HexImage, actual: HexImage, dev: McuDevice) -> None:
        eflat = expected.to_flat()
        aflat = actual.to_flat()
        mismatches = []
        for address, wanted in eflat.items():
            if address == dev.config_start + 6:  # silicon ID slot is read-only
                continue
            if address not in aflat:
                mismatches.append((address, wanted, None))
            elif address >= dev.data_start:
                if (aflat[address] & 0xFF) != (wanted & 0xFF):
                    mismatches.append((address, wanted, aflat[address]))
            elif (aflat[address] & 0x3FFF) != (wanted & 0x3FFF):
                mismatches.append((address, wanted, aflat[address]))
            if len(mismatches) >= 8:
                break
        if mismatches:
            detail = ", ".join(
                f"0x{addr:04X}: expected {want:04X}, got {got if got is not None else 'missing'}"
                for addr, want, got in mismatches
            )
            raise ProtocolError("Read-back verification failed: " + detail)

    def program_hex(self, image: HexImage, dev: McuDevice, progress: Progress = None,
                    pct: Percent = None, do_verify: bool = True,
                    force_calibration: bool = False) -> str:
        port = self._require_connected()
        gate_hex_fits(image.to_flat(), dev)
        if pct:
            pct(0, 1)
        source = self._write_temp_hex(image)
        try:
            args = ["--pic-serial-port", port, "--device", dev.name, "--erase", "--burn",
                    "--input-hexfile", str(source)]
            if force_calibration:
                args.append("--force-calibration")
            output = self._checked(args, progress)
        finally:
            source.unlink(missing_ok=True)
        if do_verify:
            if progress:
                progress("Read-back verify: reading target and comparing written addresses…")
            # Verification must still run if the user requested cancellation
            # while the write subprocess was active; never skip post-write checks.
            readback = self._readback(dev, progress, check_cancel=False)
            self._compare(image, readback, dev)
        if pct:
            pct(1, 1)
        return "Programming complete; read-back verification passed and host closed its serial port."

    def verify_hex(self, image: HexImage, dev: McuDevice, progress: Progress = None,
                   pct: Percent = None, force_calibration: bool = False) -> str:
        gate_hex_fits(image.to_flat(), dev)
        readback = self._readback(dev, progress)
        self._compare(image, readback, dev)
        if pct:
            pct(1, 1)
        return f"Read-back verification passed for {dev.display_name}."

    def read_chip(self, dev: McuDevice, progress: Progress = None,
                  pct: Percent = None) -> Dict[str, Dict[int, int]]:
        image = self._readback(dev, progress)
        flat = image.to_flat()
        result = {
            "program": {a: v for a, v in flat.items() if dev.in_program(a)},
            "config": {a: v for a, v in flat.items() if dev.in_config(a)},
            "data": {a: v for a, v in flat.items() if dev.in_data(a)},
        }
        if pct:
            pct(1, 1)
        return result

    def blank_check(self, dev: McuDevice, progress: Progress = None,
                    pct: Percent = None) -> Tuple[bool, str]:
        regions = self.read_chip(dev, progress=progress)
        used = {**regions["program"], **regions["config"], **regions["data"]}
        nonblank = []
        for addr, value in used.items():
            blank = 0xFF if dev.in_data(addr) else 0x3FFF
            if value != blank and addr != dev.config_start + 6:
                nonblank.append(addr)
                if len(nonblank) >= 8:
                    break
        if pct:
            pct(1, 1)
        if nonblank:
            return False, "Device is not blank; first nonblank address: " + ", ".join(f"0x{x:04X}" for x in nonblank)
        return True, f"{dev.display_name} appears blank (device ID slot ignored)."

    def erase_chip(self, dev: McuDevice, preserve_calibration: bool = True,
                   progress: Progress = None, pct: Percent = None) -> str:
        port = self._require_connected()
        args = ["--pic-serial-port", port, "--device", dev.name, "--erase"]
        if not preserve_calibration:
            # Upstream requires a HEX image with the calibration word before
            # force-erasing it. Never issue NOPRESERVE blindly.
            raise SafetyViolation("Cannot erase calibration without first reading and explicitly supplying its factory word.")
        output = self._checked(args, progress)
        if pct:
            pct(1, 1)
        return output or f"{dev.display_name} erased with factory calibration preservation."
