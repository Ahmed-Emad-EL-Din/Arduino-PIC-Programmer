import unittest

from core.serial_link import SerialPortInfo


class TestSerialPortInfo(unittest.TestCase):
    def test_ch340_com_port_is_recognized_as_an_arduino_candidate(self):
        port = SerialPortInfo("COM4", "USB-SERIAL CH340 (COM4)", "USB VID:PID=1A86:7523")
        self.assertTrue(port.is_likely_arduino)
        self.assertIn("COM4", port.label())

    def test_wch_descriptor_is_recognized_even_without_ch340_name(self):
        port = SerialPortInfo("COM12", "USB Serial Device", "USB VID:PID=1A86:5523")
        self.assertTrue(port.is_likely_arduino)


if __name__ == "__main__":
    unittest.main()
