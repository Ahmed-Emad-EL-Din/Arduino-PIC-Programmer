"""Hardware-safety interlocks.

Central place for every rule that prevents damage to real silicon.
GUI and worker layers must consult these gates; they never bypass them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .ihex import HexImage
from .mcu_db import McuDevice
from .pinout_db import MODE_ICSP, MODE_ZIF_18, MODE_ZIF_8, get_board_wiring, get_pic_wiring
from .protocol import DeviceInfo, ProgrammerNotReady


class SafetyViolation(RuntimeError):
    """A required safety condition is not met — operation must not run."""


@dataclass
class PreflightItem:
    id: str
    text: str
    critical: bool = True


# Static fallback checklist (for callers without specific MCU context)
ZIF_PREFLIGHT: List[PreflightItem] = [
    PreflightItem("vpp_led",
                  "13 V VPP programming supply is connected to JP1 (NEVER to "
                  "the Arduino barrel jack!) and the VPP indicator LED is ON."),
    PreflightItem("power",
                  "Arduino is powered via USB and will NOT be unplugged during "
                  "the operation."),
    PreflightItem("socket",
                  "Target PIC is seated with Pin 1 oriented correctly (notch/dot) "
                  "and the ZIF lever is locked (or ICSP wires verified)."),
    PreflightItem("jumper",
                  "Jumper JP3 matches the target package: 1-2 for 18-pin PICs "
                  "(e.g. PIC16F84A), 2-3 for 8-pin PICs (e.g. PIC12F675), or "
                  "ICSP cable used for 14/20/28/40-pin devices."),
    PreflightItem("no_touch",
                  "Nothing conductive is touching the ZIF/ICSP contacts and "
                  "the circuit sits on an insulated surface."),
    PreflightItem("voltage",
                  "Target PIC is a 5 V VDD / 13 V VPP device from the supported "
                  "list (NEVER connect a 3.3 V-only MCU to 13 V VPP)."),
]

SOFT_PREFLIGHT: List[PreflightItem] = [
    PreflightItem("port",
                  "Selected serial port is the Arduino running ProgramPic "
                  "(not another serial peripheral)."),
    PreflightItem("app",
                  "Arduino Serial Monitor, MPLAB IPE, QPICkit, and any other "
                  "serial terminal on this port are closed."),
]


def build_dynamic_preflight(dev: McuDevice, board_key: str = "uno") -> List[PreflightItem]:
    """Build a tailored, hardware-accurate preflight checklist for the exact
    selected Arduino board and Target PIC MCU."""
    pw = get_pic_wiring(dev.name)
    bw = get_board_wiring(board_key)
    items: List[PreflightItem] = [
        PreflightItem(
            "port_exclusive",
            f"Port belongs to {bw.board_name} running ProgramPic v1.8.horo, "
            "and Arduino Serial Monitor / MPLAB / QPICkit are closed.",
        ),
        PreflightItem(
            "vpp_rail",
            "External 13 V DC VPP supply is connected ONLY to programmer "
            "header JP1 (polarity verified, red VPP LED lit — NEVER plugged "
            "into the Arduino's power pin).",
        ),
    ]

    if not dev.has_device_id:
        items.append(PreflightItem(
            "manual_no_id",
            f"{dev.display_name} has no silicon Device ID. The programmer cannot electronically distinguish it from other no-ID PICs; verify the package marking and target selection before any erase or write.",
        ))

    if pw.mode == MODE_ZIF_18:
        items.append(PreflightItem(
            "zif_18",
            f"{dev.display_name} ({pw.package}) is seated in the 18-pin ZIF "
            f"socket with Pin 1 at top-left (notch up), lever locked, and "
            f"Jumper JP3 set to 1-2 (routes D2 VDD to Pin 14)."
        ))
    elif pw.mode == MODE_ZIF_8:
        items.append(PreflightItem(
            "zif_8",
            f"{dev.display_name} ({pw.package}) is seated in the 8-pin ZIF "
            f"zone (Pin 1=VDD, Pin 4=MCLR, Pin 8=VSS) AND Jumper JP3 is set "
            f"to 2-3 (routes D2 VDD to Pin 1 — wrong JP3 damages the chip!)."
        ))
    else:
        if not pw.pinout_verified:
            items.append(PreflightItem(
                "datasheet_pinout",
                f"Pin-level wiring for {dev.display_name} is not verified by this app. "
                "Use the exact manufacturer's datasheet to identify every VDD, VSS, "
                "MCLR/VPP, PGC, and PGD pin before connecting; do not rely on a generic diagram.",
            ))
        else:
            vdd_s = ", ".join(str(p) for p in pw.vdd_pins)
            vss_s = ", ".join(str(p) for p in pw.vss_pins)
            pgm_s = (f", and Pin {pw.pgm_pin} (PGM) pulled to GND via 4.7 kΩ"
                     if pw.pgm_pin else "")
            items.append(PreflightItem(
                "icsp_wiring",
                f"{dev.display_name} ({pw.package}) is wired via ICSP / breadboard "
                f"(NOT plugged into the 18-pin ZIF socket!): MCLR/VPP=Pin {pw.vpp_pin}, "
                f"VDD=Pin {vdd_s} (+100nF), VSS=Pin {vss_s}, PGC=Pin {pw.pgc_pin} "
                f"({bw.clk_pin}), PGD=Pin {pw.pgd_pin} ({bw.data_pin}){pgm_s}."
            ))

    if dev.reserved_words > 0:
        items.append(PreflightItem(
            "osccal",
            f"Factory oscillator calibration word at 0x{dev.reserved_start:04X} "
            f"will be automatically read and preserved across erase/write.",
        ))

    items.append(PreflightItem(
        "5v_hv_safe",
        f"Confirmed {dev.display_name} is a 5 V tolerant PIC (never 3.3 V-only "
        "silicon). Keep USB connected until the host operation finishes; this app does not measure socket voltage, so verify external VPP is off before handling the target.",
    ))
    return items


def gate_programmer_verified(verified: bool) -> None:
    if not verified:
        raise SafetyViolation(
            "Programmer not verified. Run Connect (handshake) first — "
            "refusing to send any command to hardware."
        )


def gate_device_match(selected: McuDevice, info: DeviceInfo) -> None:
    """Hard gate: silicon must match the selected MCU before write/erase.

    The raw ID is unavailable when using the legacy host CLI. In that case the
    adapter must rely on the host's own selected-device check; this helper will
    not fabricate an ID from the MCU database.

    Two modes:
      * ID-bearing chips (e.g. PIC16F84A, ID 0x0560): strict match or block.
      * No-ID chips (e.g. PIC16F84): silicon can only prove presence
        (ID = 0x0000) — we allow it when DeviceID == 0x0000 and force the
        memory map with SETDEVICE. ID 0x3FFF (all ones) is always rejected.
    """
    if info.device_id is None:
        raise SafetyViolation(
            "Raw silicon ID is unavailable from the host adapter; use the upstream host's own target-match check."
        )
    if info.device_id == 0x3FFF:
        raise SafetyViolation(
            "Device ID reads 0x3FFF (all ones): empty socket, missing 13 V VPP, "
            "wrong JP3 jumper, or reversed orientation. Refusing to continue."
        )
    if selected.device_id >= 0:
        if info.device_id == 0:
            raise SafetyViolation(
                f"No device ID (0x0000) read, but {selected.display_name} "
                f"always reports ID 0x{selected.device_id:04X}. Check 13 V VPP, "
                "JP3 jumper, socket seating, or code protection. Refusing operation."
            )
        if not selected.matches_id(info.device_id):
            from .mcu_db import find_by_id
            detected = find_by_id(info.device_id)
            det = detected.display_name if detected else \
                f"unknown ID 0x{info.device_id:04X}"
            raise SafetyViolation(
                f"Silicon in socket reports {det} (ID 0x{info.device_id:04X}), "
                f"but {selected.display_name} (ID 0x{selected.device_id:04X}) "
                "is selected. Refusing operation to protect hardware and data."
            )
    else:
        if info.device_id != 0:
            from .mcu_db import find_by_id
            detected = find_by_id(info.device_id)
            det = f" ({detected.display_name})" if detected else ""
            raise SafetyViolation(
                f"Selected {selected.display_name} (no device ID expected), "
                f"but silicon reported ID 0x{info.device_id:04X}{det}. "
                "Select the matching MCU before continuing."
            )


def gate_hex_fits(flat: Dict[int, int], dev: McuDevice) -> None:
    """The image (FLAT word address space) must only touch regions that
    exist on the target. `flat` comes from HexImage.to_flat()."""
    if not flat:
        raise SafetyViolation("HEX file contains no data — nothing to program.")
    problems: List[str] = []
    for addr in sorted(flat):
        if dev.region_of(addr) is None:
            problems.append(f"0x{addr:04X}")
    if problems:
        sample = ", ".join(problems[:5])
        more = f" (+{len(problems)-5} more)" if len(problems) > 5 else ""
        raise SafetyViolation(
            f"HEX word addresses outside {dev.display_name} memory map: "
            f"{sample}{more}. Wrong HEX file for {dev.display_name}?"
        )


def analyze_hex_for_device(img: HexImage, dev: McuDevice) -> Dict[str, object]:
    """Inspect how a HexImage maps onto `dev` regions without touching hardware."""
    flat = img.to_flat()
    prog_defined = [a for a in flat if dev.in_program(a)]
    cfg_defined = [a for a in flat if dev.in_config(a) and a != dev.config_start + 6]
    data_defined = [a for a in flat if dev.in_data(a)]
    out_of_range = [a for a in flat if dev.region_of(a) is None]
    touches_cal = [
        a for a in prog_defined
        if dev.reserved_words > 0 and a >= dev.reserved_start
    ]
    cfg_word_addr = dev.config_start + 7
    cfg_word = (flat[cfg_word_addr] & 0x3FFF) if cfg_word_addr in flat else None
    warnings = []
    if touches_cal:
        warnings.append(
            f"HEX includes reserved calibration address 0x{touches_cal[0]:04X} "
            f"(factory OSCCAL preserved automatically unless unchecked)."
        )
    if cfg_word is None:
        warnings.append(
            f"HEX omits configuration fuse word 0x{cfg_word_addr:04X} (defaults to 0x3FFF)."
        )
    return {
        "prog_words": len(prog_defined),
        "prog_words_used": len(prog_defined),
        "prog_words_total": dev.program_words,
        "cfg_words": len(cfg_defined),
        "cfg_words_used": len(cfg_defined),
        "cfg_words_total": dev.config_words,
        "data_bytes": len(data_defined),
        "data_bytes_used": len(data_defined),
        "data_bytes_total": dev.data_bytes,
        "out_of_range": out_of_range,
        "touches_calibration": touches_cal,
        "warnings": warnings,
        "config_word": cfg_word,
        "fits": len(out_of_range) == 0 and len(flat) > 0,
    }


def gate_not_blank_only(img: HexImage) -> None:
    if img.size() == 0:
        raise SafetyViolation("HEX is empty.")


def build_summary(selected: McuDevice, img: HexImage,
                  info: Optional[DeviceInfo] = None,
                  do_verify: bool = True,
                  preserve_calibration: bool = True) -> str:
    stats = analyze_hex_for_device(img, selected)
    lines = [
        f"Target MCU:      {selected.display_name} "
        f"({selected.program_words} words Flash, "
        f"{selected.data_bytes} B EEPROM)",
        f"HEX payload:     {stats['prog_words_used']}/{selected.program_words} Flash words, "
        f"{stats['data_bytes_used']}/{selected.data_bytes} EEPROM entries, "
        f"{stats['cfg_words_used']} config word(s)",
    ]
    if stats["config_word"] is not None:
        lines.append(f"HEX ConfigWord:  0x{stats['config_word']:04X}")
    if selected.reserved_words > 0:
        if preserve_calibration:
            lines.append(
                f"Calibration:     Preservation requested at 0x{selected.reserved_start:04X}-"
                f"0x{selected.program_end:04X} (host behavior not hardware-validated)"
            )
        else:
            lines.append("Calibration:     Preservation disabled; calibration may be overwritten.")
    if info is not None:
        if info.device_id is not None:
            lines.append(f"Silicon ID:      0x{info.device_id:04X}"
                         + (f" ({info.device_name})" if info.device_name else ""))
        elif info.device_name:
            lines.append(f"Host-reported:   {info.device_name} (raw ID unavailable)")
    sequence = "Host sequence:   selected device map -> erase -> write (Flash -> EEPROM -> Config)"
    sequence += " -> read-back compare" if do_verify else " -> read-back verify disabled"
    lines.append(sequence + " -> normal host shutdown")
    lines.append("Hardware check:  raw target ID and socket voltage are not exposed to this app.")
    lines.append("Before handling: independently verify the external VPP supply is off.")
    return "\n".join(lines)


# Confirmation text builders -------------------------------------------------

def confirm_erase_text(dev: McuDevice) -> Tuple[str, str]:
    title = f"Erase {dev.display_name}"
    cal_note = (
        f"Calibration preservation is requested for the reserved region beginning at "
        f"0x{dev.reserved_start:04X}; verify this behavior for the exact device and firmware."
        if dev.reserved_words > 0 or dev.config_save_mask != 0
        else "Check the selected device datasheet for erase effects on IDs and configuration."
    )
    body = (
        f"Erase all user memory on {dev.display_name}?\n\n"
        "  • Program Flash memory will be cleared to 0x3FFF\n"
        "  • Data EEPROM will be cleared to 0xFF\n"
        "  • User ID & Configuration fuses will be reset\n\n"
        f"{cal_note}\n"
        "The host uses the selected device model; raw silicon ID is not exposed to this app. "
        "On normal shutdown the host requests power-off, but the app cannot measure socket voltage. "
        "Verify the external VPP supply is off before touching the target."
    )
    return title, body


def confirm_program_text(dev: McuDevice, hex_name: str, do_verify: bool = True,
                         preserve_calibration: bool = True) -> Tuple[str, str]:
    title = f"Program & Verify {dev.display_name}"
    verification = (
        "Read-back comparison is enabled."
        if do_verify else "WARNING: read-back comparison is disabled."
    )
    calibration = (
        "Calibration preservation is requested; verify behavior for this exact PIC and firmware."
        if preserve_calibration else "WARNING: calibration preservation is disabled; calibration may be overwritten."
    )
    body = (
        f"Write '{hex_name}' to selected target {dev.display_name}?\n\n"
        "  1. Use the selected device map (raw silicon ID is not exposed to this app)\n"
        "  2. Erase and write Flash, EEPROM, and configuration data\n"
        f"  3. {verification}\n"
        f"  4. {calibration}\n"
        "  5. Close the host normally (it requests power-off on shutdown)\n\n"
        "The app cannot measure socket voltage. Verify the external VPP supply is off "
        "before touching the target. Keep USB connected until the host operation finishes."
    )
    return title, body


def confirm_flash_arduino(board_label: str, port: str) -> Tuple[str, str]:
    title = "Flash Arduino Programmer Firmware"
    body = (
        f"Erase the sketch on {port} and upload ProgramPic v1.8.horo for "
        f"{board_label}?\n\n"
        "Note: Remove any 2.2 uF RESET-to-GND capacitor while flashing the "
        "Arduino bootloader, then reconnect it afterwards for PIC programming."
    )
    return title, body


def classify_exception(exc: BaseException) -> str:
    """Map exceptions to user-facing, actionable messages."""
    from .protocol import ProgrammerNotReady, ProtocolError
    from .serial_link import LinkTimeout, LinkError
    from .avrdude import FlashError
    if isinstance(exc, SafetyViolation):
        return f"SAFETY GATE — {exc}"
    if isinstance(exc, ProgrammerNotReady):
        return f"NOT CONNECTED — {exc}"
    if isinstance(exc, LinkTimeout):
        return f"TIMEOUT — {exc}"
    if isinstance(exc, LinkError):
        return f"SERIAL LINK — {exc}"
    if isinstance(exc, FlashError):
        return f"ARDUINO FLASH — {exc}"
    if isinstance(exc, ProtocolError):
        return f"PROGRAMMER — {exc}"
    return f"ERROR — {exc}"
