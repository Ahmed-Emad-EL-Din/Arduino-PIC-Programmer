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
