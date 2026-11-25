import unittest
import xml.etree.ElementTree as ET

from core.circuit_drawer import generate_package_pinout_svg, generate_schematic_svg
from core.mcu_db import DEFAULT_DEVICE
from core.pinout_db import get_pic_wiring


class TestSvgDiagrams(unittest.TestCase):
    def test_known_device_schematic_and_pinout_are_valid_svg(self):
        schematic = generate_schematic_svg(DEFAULT_DEVICE.name, "uno", "dark")
        pinout = generate_package_pinout_svg(DEFAULT_DEVICE.name, "uno", "light")
        self.assertEqual(ET.fromstring(schematic).tag, "{http://www.w3.org/2000/svg}svg")
        self.assertEqual(ET.fromstring(pinout).tag, "{http://www.w3.org/2000/svg}svg")
        self.assertTrue(get_pic_wiring(DEFAULT_DEVICE.name).pinout_verified)

    def test_unknown_package_does_not_fabricate_pin_numbers(self):
        svg = generate_package_pinout_svg("pic16f883")
        root = ET.fromstring(svg)
        text = " ".join(node.text or "" for node in root.iter())
        self.assertIn("not verified", text)
        self.assertFalse(get_pic_wiring("pic16f883").pinout_verified)


if __name__ == "__main__":
    unittest.main()
