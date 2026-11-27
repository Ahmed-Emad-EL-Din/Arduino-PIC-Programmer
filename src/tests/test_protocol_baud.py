import inspect
from pathlib import Path

from core.programmer import ProgrammerSession


ROOT = Path(__file__).resolve().parents[2]


def test_program_pic_firmware_and_host_default_to_9600_baud():
    firmware = (ROOT / "firmware/source/ProgramPic/ProgramPic.ino").read_text(encoding="utf-8")
    host = (ROOT / "vendor/ArdPicProg/main.cpp").read_text(encoding="utf-8")

    assert "Serial.begin( 9600 );" in firmware
    assert "int opt_speed = 9600;" in host
    assert inspect.signature(ProgrammerSession.connect).parameters["baud"].default == 9600


def test_program_pic_wiring_profile_matches_pic16f84a_shield_connection():
    firmware = (ROOT / "firmware/source/ProgramPic/ProgramPic.ino").read_text(encoding="utf-8")

    # Keep these assignments in lockstep with the user-provided shield wiring:
    # A1 controls the external VPP switch, D2 supplies VDD, D4/D7 are ICSP,
    # and A5 drives the activity LED. The polarity is specific to that switch.
    for definition in (
        "#define PIN_MCLR     A1",
        "#define PIN_ACTIVITY A5",
        "#define PIN_VDD      2",
        "#define PIN_CLOCK    4",
        "#define PIN_DATA     7",
        "#define MCLR_RESET   HIGH",
        "#define MCLR_VPP     LOW",
    ):
        assert definition in firmware

    # PIC16F84A uses MCLR-first high-voltage entry on this wiring profile.
    assert '{s_pic16f84a, 0x0560, 1024, 0x2000, 0x2100, 8, 64, 0, 0, FLASH, EEPROM, MCLR_first}' in firmware
    entry = firmware.split("void enterProgramMode() {", 1)[1].split("void exitProgramMode()", 1)[0]
    assert entry.index("digitalWrite(PIN_MCLR, MCLR_RESET)") < entry.index("digitalWrite(PIN_VDD, LOW)")
    assert entry.index("digitalWrite(PIN_MCLR, MCLR_VPP)") < entry.index("digitalWrite(PIN_VDD, HIGH)")
    assert "digitalWrite(PIN_MCLR, MCLR_RESET);" in firmware.split("void exitProgramMode()", 1)[1]


def test_icsp_write_bits_are_set_up_before_the_rising_clock_edge():
    firmware = (ROOT / "firmware/source/ProgramPic/ProgramPic.ino").read_text(encoding="utf-8")

    send_command = firmware.split("void sendCommand(byte cmd)", 1)[1].split("void sendSimpleCommand", 1)[0]
    send_write = firmware.split("void sendWriteCommand(byte cmd, unsigned int data)", 1)[1].split("void sendReadCommand", 1)[0]
    for routine in (send_command, send_write):
        data_set = routine.index("digitalWrite(PIN_DATA,")
        setup_delay = routine.index("delayMicroseconds(DELAY_TSET1)")
        rising_edge = routine.index("digitalWrite(PIN_CLOCK, HIGH)")
        assert data_set < setup_delay < rising_edge
