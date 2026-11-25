import unittest

from core.mcu_db import lookup
from core.protocol import DeviceInfo
from core.safety import SafetyViolation, build_dynamic_preflight, gate_device_match


class TestSafetyGates(unittest.TestCase):
    def test_raw_id_match_and_mismatch(self):
        expected = lookup("pic16f84a")
        gate_device_match(expected, DeviceInfo(device_id=0x0567))
        with self.assertRaises(SafetyViolation):
            gate_device_match(expected, DeviceInfo(device_id=0x10C1))

    def test_blank_id_and_unavailable_id_are_blocked(self):
        expected = lookup("pic16f84a")
        with self.assertRaises(SafetyViolation):
            gate_device_match(expected, DeviceInfo(device_id=0x3FFF))
        with self.assertRaises(SafetyViolation):
            gate_device_match(expected, DeviceInfo(device_id=None))

    def test_no_id_chip_requires_explicit_manual_selection(self):
        no_id = lookup("pic16f84")
        gate_device_match(no_id, DeviceInfo(device_id=0))
        with self.assertRaises(SafetyViolation):
            gate_device_match(no_id, DeviceInfo(device_id=0x0560))

    def test_no_id_target_gets_manual_identity_warning(self):
        items = build_dynamic_preflight(lookup("pic16f84"), "uno")
        manual = next(item for item in items if item.id == "manual_no_id")
        self.assertTrue(manual.critical)
        self.assertIn("cannot electronically distinguish", manual.text)

    def test_unknown_pinout_is_called_out_in_preflight(self):
        items = build_dynamic_preflight(lookup("pic16f883"), "uno")
        pinout = next(item for item in items if item.id == "datasheet_pinout")
        self.assertTrue(pinout.critical)
        self.assertIn("datasheet", pinout.text.lower())
        self.assertNotIn("Pin None", " ".join(item.text for item in items))


if __name__ == "__main__":
    unittest.main()
