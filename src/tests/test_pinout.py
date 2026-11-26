import re
import unittest
from pathlib import Path

from core.circuit_drawer import generate_schematic_svg
from core.pinout_db import BOARDS, build_wiring_rows


class TestFirmwarePinout(unittest.TestCase):
    def test_application_wiring_metadata_matches_requested_profile(self):
        for board in BOARDS.values():
            with self.subTest(board=board.board_key):
                self.assertEqual(board.vdd_pin, "D2")
                self.assertEqual(board.mclr_pin, "A1")
                self.assertEqual(board.clk_pin, "D4")
                self.assertEqual(board.data_pin, "D7")
                self.assertEqual(board.activity_pin, "A5")

    def test_uploaded_sketch_defines_requested_pins_and_active_low_vpp(self):
        sketch = (
            Path(__file__).resolve().parents[2]
            / "firmware"
            / "source"
            / "ProgramPic"
            / "ProgramPic.ino"
        ).read_text(encoding="utf-8")
        expected = {
            "PIN_ACTIVITY": "A5",
            "PIN_VDD": "2",
            "PIN_MCLR": "A1",
            "PIN_CLOCK": "4",
            "PIN_DATA": "7",
            "MCLR_RESET": "HIGH",
            "MCLR_VPP": "LOW",
        }
        for name, value in expected.items():
            with self.subTest(define=name):
                self.assertRegex(
                    sketch,
                    rf"(?m)^\s*#define\s+{name}\s+{value}\b",
                )

    def test_generated_wiring_diagram_uses_requested_mapping_and_separate_vpp_switch(self):
        svg = generate_schematic_svg("pic16f84a", "nano_new").decode("utf-8")
        for label in ("D2  switched +5 V VDD", "A1  MCLR/VPP switch control", "D4  PGC / clock", "D7  PGD / bidirectional data", "A5  activity LED"):
            with self.subTest(label=label):
                self.assertIn(label, svg)
        self.assertIn("switched VPP output goes to PIC MCLR", svg)
        self.assertNotIn("D3  MCLR", svg)
        self.assertNotIn("D5  PGD", svg)

    def test_pic16f84a_wiring_rows_describe_power_and_safe_vpp_control(self):
        rows = {signal: (source, target, note)
                for signal, source, target, note in build_wiring_rows("nano_new", "pic16f84a")}
        self.assertEqual(rows["VDD"][1], "14")
        self.assertIn("100 nF", rows["VDD"][2])
        self.assertIn("PIC Pin 4", rows["MCLR / VPP"][1])
        self.assertIn("HIGH=reset", rows["MCLR / VPP"][2])
        self.assertIn("Never connect VPP", rows["MCLR / VPP"][2])
        self.assertIn("PIC Pin 12", rows["CLK / PGC"][1])
        self.assertIn("PIC Pin 13", rows["DATA / PGD"][1])
        self.assertIn("A5", rows["Activity LED"][0])
        self.assertEqual(rows["VSS / GND"][1], "5")


if __name__ == "__main__":
    unittest.main()
