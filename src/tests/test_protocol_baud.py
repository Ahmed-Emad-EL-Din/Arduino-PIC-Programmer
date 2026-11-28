import inspect
from pathlib import Path
from unittest.mock import patch

from app.settings import AppSettings
from core.programmer import ProgrammerSession
from core.protocol import ProgrammerNotReady
from core.serial_config import PROGRAMMER_BAUD


ROOT = Path(__file__).resolve().parents[2]


def test_program_pic_runtime_link_and_host_default_to_9600_baud():
    firmware = (ROOT / "firmware/source/ProgramPic/ProgramPic.ino").read_text(encoding="utf-8")
    host = (ROOT / "vendor/ArdPicProg/main.cpp").read_text(encoding="utf-8")

    assert "Serial.begin( 9600 );" in firmware
    assert "int opt_speed = 9600;" in host
    assert inspect.signature(ProgrammerSession.connect).parameters["baud"].default == PROGRAMMER_BAUD


def test_runtime_connection_always_uses_9600_and_rejects_bootloader_rates():
    session = ProgrammerSession()
    with patch.object(session, "_checked", return_value="Supported devices:") as checked:
        session.connect("COM4")
    assert checked.call_args.args[0] == [
        "--pic-serial-port", "COM4", "--speed", PROGRAMMER_BAUD, "--list-devices"
    ]

    try:
        session.connect("COM4", baud=115200)
    except ProgrammerNotReady as exc:
        assert "requires 9600 baud" in str(exc)
    else:
        raise AssertionError("A bootloader baud must not be used for runtime connection")


def test_saved_custom_baud_is_forced_back_to_program_pic_rate():
    class MemorySettings:
        def __init__(self, *_args):
            self.values = {"baud": 115200, "baud_9600_migrated": True}

        def beginGroup(self, _group):
            pass

        def setValue(self, key, value):
            self.values[key] = value

        def value(self, key, default=None, **_kwargs):
            return self.values.get(key, default)

        def sync(self):
            pass

    with patch("app.settings.QSettings", MemorySettings):
        settings = AppSettings()
        assert settings.baud == PROGRAMMER_BAUD
        assert settings._settings.values["baud"] == PROGRAMMER_BAUD
        settings.baud = 115200
        assert settings.baud == PROGRAMMER_BAUD
        assert settings._settings.values["baud"] == PROGRAMMER_BAUD


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
