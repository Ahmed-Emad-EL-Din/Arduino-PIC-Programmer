import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from core.drawio import DrawioRenderError, drawio_to_svg


ROOT = Path(__file__).resolve().parents[2]
DIAGRAM = ROOT / "assets" / "reference" / "user-circuit-diagram.drawio"


class TestDrawioRenderer(unittest.TestCase):
    def test_bundled_xml_renders_as_offline_svg_with_wires_and_embedded_art(self):
        svg = drawio_to_svg(DIAGRAM)
        root = ET.fromstring(svg)
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertGreaterEqual(len(root.findall(".//{http://www.w3.org/2000/svg}image")), 3)
        self.assertGreaterEqual(len(root.findall(".//{http://www.w3.org/2000/svg}polyline")), 20)
        self.assertIn(b"24V DC", svg)
        self.assertIn(b"supply", svg)
        self.assertNotIn(b"https://", svg)

    def test_missing_file_reports_clear_render_error(self):
        with self.assertRaises(DrawioRenderError):
            drawio_to_svg(ROOT / "missing-circuit.drawio")


if __name__ == "__main__":
    unittest.main()
