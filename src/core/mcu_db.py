"""Target MCU database for the ArdPicProg-compatible programmer.

Mirrors the device table in Ho-Ro/ArdPicProg ProgramPic sketch (v1.8.horo).
Device IDs are matched with mask 0xFFE0 (same as the firmware).
All sizes are in WORDS for program/config memory and BYTES for EEPROM data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

ID_MASK = 0xFFE0

FLASH, FLASH4, FLASH5, FLASH8 = 1, 4, 5, 8
EEPROM = 0
MCLR_FIRST, VDD_FIRST = 0, 1

FLASH_TYPE_NAMES = {FLASH: "FLASH", FLASH4: "FLASH4", FLASH5: "FLASH5", FLASH8: "FLASH8"}
ENTRY_MODE_NAMES = {MCLR_FIRST: "MCLR first", VDD_FIRST: "VDD first"}


@dataclass(frozen=True)
class McuDevice:
    name: str                 # e.g. "pic16f84a" (firmware spelling, lowercase)
    display_name: str          # e.g. "PIC16F84A"
    device_id: int             # -1 => no ID (must use SETDEVICE)
    program_words: int         # program memory size in words
    config_start: int          # flat address
    config_words: int
    data_start: int            # flat address of EEPROM
    data_bytes: int
    reserved_words: int        # e.g. OSCCAL/cal words at end of flash
    config_save_mask: int      # bits of config word preserved on erase
    prog_flash_type: int
    data_flash_type: int
    entry_mode: int
    family: str                # "PIC10/12/14/16" etc. for UI grouping

    @property
    def config_end(self) -> int:
        return self.config_start + self.config_words - 1

    @property
    def data_end(self) -> int:
        return self.data_start + self.data_bytes - 1

    @property
    def program_end(self) -> int:
        return self.program_words - 1

    @property
    def reserved_start(self) -> int:
        return self.program_words - self.reserved_words

    @property
    def has_device_id(self) -> bool:
        return self.device_id >= 0

    def matches_id(self, raw_id: int) -> bool:
        if self.device_id < 0:
            return False
        return (raw_id & ID_MASK) == (self.device_id & ID_MASK)

    def in_program(self, addr: int) -> bool:
        return 0 <= addr <= self.program_end

    def in_config(self, addr: int) -> bool:
        return self.config_start <= addr <= self.config_end

    def in_data(self, addr: int) -> bool:
        return self.data_start <= addr <= self.data_end

    def region_of(self, addr: int) -> Optional[str]:
        if self.in_program(addr):
            return "program"
        if self.in_config(addr):
            return "config"
        if self.in_data(addr):
            return "data"
        return None


def _d(name, did, prog, cfg_s, cfg_n, data_s, data_n, res, csave, pft, dft, entry, family):
    disp = "PIC" + name[3:].upper() if name.startswith("pic") else name.upper()
    return McuDevice(name, disp, did, prog, cfg_s, cfg_n, data_s, data_n,
                     res, csave, pft, dft, entry, family)


# Table transcribed from ProgramPic.ino (Ho-Ro/ArdPicProg @ main).
_DEVICES: List[McuDevice] = [
    _d("pic12f629", 0x0F80, 1024, 0x2000, 8, 0x2100, 128, 1, 0x3E00, FLASH4, EEPROM, MCLR_FIRST, "PIC12F"),
    _d("pic12f675", 0x0FC0, 1024, 0x2000, 8, 0x2100, 128, 1, 0x3E00, FLASH4, EEPROM, MCLR_FIRST, "PIC12F"),
    _d("pic12f683", 0x0460, 2048, 0x2000, 9, 0x2100, 256, 0, 0, FLASH4, EEPROM, MCLR_FIRST, "PIC12F"),
    _d("pic16f630", 0x10C0, 1024, 0x2000, 8, 0x2100, 128, 1, 0x3E00, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f676", 0x10E0, 1024, 0x2000, 8, 0x2100, 128, 1, 0x3E00, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f84", -1, 1024, 0x2000, 8, 0x2100, 64, 0, 0, FLASH, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f84a", 0x0560, 1024, 0x2000, 8, 0x2100, 64, 0, 0, FLASH, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f87", 0x0720, 4096, 0x2000, 9, 0x2100, 256, 0, 0, FLASH5, EEPROM, VDD_FIRST, "PIC16F"),
    _d("pic16f88", 0x0760, 4096, 0x2000, 9, 0x2100, 256, 0, 0, FLASH5, EEPROM, VDD_FIRST, "PIC16F"),
    _d("pic16f627", 0x07A0, 1024, 0x2000, 8, 0x2100, 128, 0, 0, FLASH, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f627a", 0x1040, 1024, 0x2000, 8, 0x2100, 128, 0, 0, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f628", 0x07C0, 2048, 0x2000, 8, 0x2100, 128, 0, 0, FLASH, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f628a", 0x1060, 2048, 0x2000, 8, 0x2100, 128, 0, 0, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f648a", 0x1100, 4096, 0x2000, 8, 0x2100, 256, 0, 0, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f684", 0x1080, 2048, 0x2000, 8, 0x2100, 256, 0, 0, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f688", 0x1180, 4096, 0x2000, 8, 0x2100, 256, 0, 0, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f690", 0x1400, 4096, 0x2000, 9, 0x2100, 256, 1, 0, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f872", 0x08E0, 2048, 0x2000, 8, 0x2100, 64, 0, 0, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f877", 0x09A0, 8192, 0x2000, 8, 0x2100, 256, 0, 0, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f877a", 0x0E20, 8192, 0x2000, 8, 0x2100, 256, 0, 0, FLASH8, EEPROM, VDD_FIRST, "PIC16F"),
    _d("pic16f882", 0x2000, 2048, 0x2000, 9, 0x2100, 128, 0, 0, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f883", 0x2020, 4096, 0x2000, 9, 0x2100, 256, 0, 0, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f884", 0x2040, 4096, 0x2000, 9, 0x2100, 256, 0, 0, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f886", 0x2060, 8192, 0x2000, 9, 0x2100, 256, 0, 0, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
    _d("pic16f887", 0x2080, 8192, 0x2000, 9, 0x2100, 256, 0, 0, FLASH4, EEPROM, MCLR_FIRST, "PIC16F"),
]

BY_NAME: Dict[str, McuDevice] = {d.name: d for d in _DEVICES}
DEVICES: List[McuDevice] = _DEVICES
DEFAULT_DEVICE = BY_NAME["pic16f84a"]


def all_devices() -> List[McuDevice]:
    return list(_DEVICES)


def devices_by_family() -> Dict[str, List[McuDevice]]:
    out: Dict[str, List[McuDevice]] = {}
    for d in _DEVICES:
        out.setdefault(d.family, []).append(d)
    return out


def find_by_id(raw_id: int) -> Optional[McuDevice]:
    for d in _DEVICES:
        if d.matches_id(raw_id):
            return d
    return None


def lookup(name: str) -> Optional[McuDevice]:
    return BY_NAME.get(name.strip().lower())


def autodetectable() -> List[McuDevice]:
    """Devices whose ID the firmware can autodetect (* in DEVICES list)."""
    return [d for d in _DEVICES if d.device_id >= 0]
