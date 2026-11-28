"""Arduino and PIC wiring metadata used by the workbench and preflight UI.

Only the explicitly listed package pinouts have verified numeric pin mappings.
Other supported silicon remains programmable through the upstream firmware,
but the UI deliberately instructs users to consult the exact datasheet rather
than inventing package pin numbers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

MODE_ZIF_8 = "zif8"
MODE_ZIF_18 = "zif18"
MODE_ICSP = "icsp"


@dataclass(frozen=True)
class BoardWiring:
    board_key: str
    board_name: str
    mcu_label: str
    vdd_pin: str = "D2"
    mclr_pin: str = "A1"
    clk_pin: str = "D4"
    data_pin: str = "D7"
    activity_pin: str = "A5"
    reset_pin: str = "RESET"
    needs_reset_cap: bool = True
    reset_cap_note: str = "Install the reset capacitor only after firmware upload."


@dataclass(frozen=True)
class PicWiring:
    name: str
    package: str
    mode: str
    vpp_pin: Optional[int]
    vdd_pins: Tuple[int, ...]
    vss_pins: Tuple[int, ...]
    pgc_pin: Optional[int]
    pgd_pin: Optional[int]
    pgm_pin: Optional[int] = None
    jp3_position: Optional[str] = None
    wiring_note: str = ""
    safety_note: str = ""
    pinout_verified: bool = False

    @property
    def uses_zif(self) -> bool:
        return self.mode in (MODE_ZIF_8, MODE_ZIF_18)


BOARDS: Dict[str, BoardWiring] = {
    "uno": BoardWiring("uno", "Arduino Uno", "ATmega328P"),
    "nano_new": BoardWiring("nano_new", "Arduino Nano (new bootloader)", "ATmega328P"),
    "nano_old": BoardWiring("nano_old", "Arduino Nano (old bootloader)", "ATmega328P"),
    "pro_mini_5v": BoardWiring(
        "pro_mini_5v", "Arduino Pro Mini (5 V / 16 MHz)", "ATmega328P",
        needs_reset_cap=False,
        reset_cap_note="Use only the 5 V / 16 MHz Pro Mini variant; a 3.3 V board is not compatible with this PIC circuit.",
    ),
    "mega2560": BoardWiring("mega2560", "Arduino Mega 2560", "ATmega2560"),
    "leonardo": BoardWiring("leonardo", "Arduino Leonardo", "ATmega32U4"),
    "micro": BoardWiring("micro", "Arduino Micro", "ATmega32U4"),
}

# Pin maps confirmed by the published ArdPicProg wiring and common DIP packages.
_VERIFIED: Dict[str, PicWiring] = {
    "pic12f629": PicWiring("pic12f629", "PDIP-8", MODE_ZIF_8, 4, (1,), (8,), 6, 7,
                            jp3_position="2-3", pinout_verified=True),
    "pic12f675": PicWiring("pic12f675", "PDIP-8", MODE_ZIF_8, 4, (1,), (8,), 6, 7,
                            jp3_position="2-3", pinout_verified=True),
    "pic12f683": PicWiring("pic12f683", "PDIP-8", MODE_ZIF_8, 4, (1,), (8,), 6, 7,
                            jp3_position="2-3", pinout_verified=True),
    "pic16f84": PicWiring("pic16f84", "PDIP-18", MODE_ZIF_18, 4, (14,), (5,), 12, 13, 10,
                           jp3_position="1-2", pinout_verified=True),
    "pic16f84a": PicWiring("pic16f84a", "PDIP-18", MODE_ZIF_18, 4, (14,), (5,), 12, 13, 10,
                            jp3_position="1-2", pinout_verified=True),
    "pic16f877": PicWiring("pic16f877", "PDIP-40", MODE_ICSP, 1, (11, 32), (12, 31), 39, 40, 36,
                            wiring_note="ICSP: MCLR/VPP=1, VDD=11/32, VSS=12/31, PGC=39, PGD=40.",
                            pinout_verified=True),
    "pic16f877a": PicWiring("pic16f877a", "PDIP-40", MODE_ICSP, 1, (11, 32), (12, 31), 39, 40, 36,
                             wiring_note="ICSP: MCLR/VPP=1, VDD=11/32, VSS=12/31, PGC=39, PGD=40.",
                             pinout_verified=True),
}


def get_board_wiring(board_key: str) -> BoardWiring:
    return BOARDS.get(board_key, BOARDS["uno"])


def get_pic_wiring(name: str) -> PicWiring:
    key = name.strip().lower()
    if key in _VERIFIED:
        return _VERIFIED[key]
    # Unknown/less common package pinouts are intentionally not guessed.
    return PicWiring(
        key, "package varies", MODE_ICSP, None, (), (), None, None,
        wiring_note=(
            "Pin-level wiring is not verified in this build. Use the exact device datasheet "
            "and the official ArdPicProg hardware documentation before connecting this target."
        ),
        safety_note="Unverified package pinout — do not connect until the device datasheet is checked.",
        pinout_verified=False,
    )


def build_wiring_rows(board_key: str, mcu_name: str) -> List[Tuple[str, str, str, str]]:
    board = get_board_wiring(board_key)
    pic = get_pic_wiring(mcu_name)
    rows = [
        ("CLK / PGC", f"Arduino {board.clk_pin}",
         f"PIC Pin {pic.pgc_pin}" if pic.pgc_pin else "PIC PGC (datasheet)", "Programming clock"),
        ("DATA / PGD", f"Arduino {board.data_pin}",
         f"PIC Pin {pic.pgd_pin}" if pic.pgd_pin else "PIC PGD (datasheet)", "Bidirectional data"),
        ("MCLR / VPP", f"Arduino {board.mclr_pin} → VPP switch",
         f"PIC Pin {pic.vpp_pin}" if pic.vpp_pin else "PIC MCLR/VPP (datasheet)",
         "HIGH=reset/VPP off; LOW selects external ~13 V VPP. Never connect VPP to Arduino."),
        ("VDD", f"Arduino {board.vdd_pin} switched +5 V",
         ", ".join(map(str, pic.vdd_pins)) if pic.vdd_pins else "All VDD pins (datasheet)",
         "Place 100 nF between target VDD and VSS."),
        ("VSS / GND", "Arduino GND / common ground",
         ", ".join(map(str, pic.vss_pins)) if pic.vss_pins else "All VSS pins (datasheet)",
         "Common Arduino, PIC, VPP and VDD-circuit ground."),
        ("Activity LED", f"Arduino {board.activity_pin} → resistor → LED anode",
         "LED cathode → GND", "Indicates serial-command and read/write activity."),
    ]
    if pic.pgm_pin:
        rows.append(("PGM", "4.7 kΩ pull-down to GND", f"PIC Pin {pic.pgm_pin}", "Low-voltage programming disabled"))
    return rows
