import unittest

from core.ihex import HexImage, IHexError
from core.mcu_db import DEFAULT_DEVICE
from core.safety import gate_hex_fits


class TestIntelHex(unittest.TestCase):
    def test_round_trip_pic_regions(self):
        flat = {0x0000: 0x1234, 0x0011: 0x2ABC, 0x2007: 0x3FFF,
                0x2100: 0xA5, 0x2101: 0x5A}
        image = HexImage.from_flat(flat)
        reparsed = HexImage.from_hex(image.to_hex())
        self.assertEqual(reparsed.to_flat(), flat)
        gate_hex_fits(reparsed.to_flat(), DEFAULT_DEVICE)

    def test_checksum_is_validated(self):
        with self.assertRaisesRegex(IHexError, "checksum"):
            HexImage.from_hex(":0100000001FF\n:00000001FF\n")

    def test_eof_is_required(self):
        with self.assertRaisesRegex(IHexError, "EOF"):
            HexImage.from_hex(":020000000102FB\n")

    def test_unpaired_pic_byte_is_rejected(self):
        image = HexImage({0: 0x34})
        with self.assertRaisesRegex(IHexError, "Unpaired"):
            image.to_flat()

    def test_conflicting_overlaps_are_rejected(self):
        text = HexImage({0: 0x34, 1: 0x12}).to_hex()
        duplicate = ":0100000035CA\n"
        with self.assertRaisesRegex(IHexError, "conflicting"):
            HexImage.from_hex(text.replace(":00000001FF", duplicate + ":00000001FF"))


if __name__ == "__main__":
    unittest.main()
