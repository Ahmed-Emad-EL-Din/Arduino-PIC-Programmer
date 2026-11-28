import base64
import struct
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ICON_PNG = ROOT / "assets" / "app-icon.png"
ICON_ICO = ROOT / "assets" / "app-icon.ico"
ICON_SVG = ROOT / "assets" / "app-icon.svg"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class TestAppIconAssets(unittest.TestCase):
    def test_square_png_and_standalone_svg_use_the_same_cropped_artwork(self):
        png = ICON_PNG.read_bytes()
        self.assertTrue(png.startswith(PNG_SIGNATURE))
        self.assertEqual(struct.unpack_from(">II", png, 16), (1024, 1024))

        root = ET.parse(ICON_SVG).getroot()
        image = root.find("{http://www.w3.org/2000/svg}image")
        self.assertIsNotNone(image)
        href = image.attrib["href"]
        prefix = "data:image/png;base64,"
        self.assertTrue(href.startswith(prefix))
        self.assertEqual(base64.b64decode(href[len(prefix):]), png)

    def test_windows_ico_contains_all_expected_square_sizes(self):
        ico = ICON_ICO.read_bytes()
        reserved, icon_type, count = struct.unpack_from("<HHH", ico)
        self.assertEqual((reserved, icon_type), (0, 1))
        entries = []
        for index in range(count):
            width, height, _colors, _reserved, _planes, _bpp, size, offset = struct.unpack_from(
                "<BBBBHHII", ico, 6 + 16 * index
            )
            width = width or 256
            height = height or 256
            payload = ico[offset:offset + size]
            self.assertEqual(len(payload), size)
            if payload.startswith(PNG_SIGNATURE):
                image_size = struct.unpack_from(">II", payload, 16)
                self.assertEqual(image_size, (width, height))
            else:
                header_size, dib_width, dib_double_height = struct.unpack_from("<Iii", payload)
                self.assertGreaterEqual(header_size, 40)
                self.assertEqual(dib_width, width)
                self.assertEqual(dib_double_height, height * 2)
            self.assertEqual(width, height)
            entries.append(width)
        self.assertEqual(sorted(entries, reverse=True), [256, 128, 64, 48, 32, 16])


if __name__ == "__main__":
    unittest.main()
