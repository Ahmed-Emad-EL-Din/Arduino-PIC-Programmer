import os
import sys
import unittest
from pathlib import Path

# Use Qt's offscreen platform in CI unless the caller explicitly selected one.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from core.mcu_db import lookup, all_devices
from core.ihex import HexImage
from gui.main_window import MainWindow
from gui.widgets.circuit_panel import CircuitPanel
from gui.dialogs.flash_arduino import FlashArduinoDialog
from gui.dialogs.preflight import PreflightDialog
from gui.dialogs.settings_dialog import SettingsDialog
from gui.dialogs.about import AboutDialog
from app import APP_NAME, ORG_NAME
from core.safety import build_dynamic_preflight


def capture_window(window, filename):
    """Save a real Qt window capture for CI review (never a synthetic mockup)."""
    output_dir = Path(os.environ.get("ARDPICPROG_SCREENSHOT_DIR", "artifacts/ui"))
    output_dir.mkdir(parents=True, exist_ok=True)
    QApplication.processEvents()
    output_path = output_dir / filename
    if not window.grab().save(str(output_path), "PNG"):
        raise AssertionError(f"Could not write UI screenshot: {output_path}")


class TestGUIIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication(sys.argv)
        cls.app.setApplicationName(APP_NAME)
        cls.app.setOrganizationName(ORG_NAME + "_Test")

    def setUp(self):
        self.win = MainWindow()
        self.win.resize(1380, 880)
        self.win.apply_theme("dark", 10)
        self.win.show()

    def tearDown(self):
        self.win.close()

    def test_main_window_initialization(self):
        self.assertEqual(self.win.settings.theme, "dark")
        self.assertIsNotNone(self.win.circuit_panel)
        self.assertIsNotNone(self.win.log_pane)
        self.assertIsNotNone(self.win.cmb_board)
        self.assertIsNotNone(self.win.cmb_mcu)
        self.assertIn("not measured", self.win.status_lbl.text())
        self.assertIn("Raw silicon ID", self.win.btn_detect.toolTip())
        self.assertIn("Target selected:", self.win.chip_target.text())
        capture_window(self.win, "main-dark-no-hardware.png")

    def test_circuit_panel_tabs(self):
        panel = self.win.circuit_panel
        self.assertEqual(panel.tabs.count(), 4)
        panel.tabs.setCurrentIndex(0)
        panel.schem_view.zoom_fit()
        panel.tabs.setCurrentIndex(1)
        panel.pinout_view.zoom_fit()
        panel.tabs.setCurrentIndex(2)
        panel.tabs.setCurrentIndex(3)

    def test_hex_image_integration(self):
        img = HexImage()
        for i in range(64):
            w = 0x3000 | (i & 0xFF)
            img.data[i * 2] = w & 0xFF
            img.data[i * 2 + 1] = (w >> 8) & 0xFF
        self.win.hex_img = img
        self.win.hex_path = "/demo/blink_pic16f84a.hex"
        self.win._refresh_hex_summary()
        self.win._refresh_actions()
        self.win.circuit_panel.set_hex_image(img)
        self.win.circuit_panel.tabs.setCurrentIndex(2)
        self.assertIn(
            "does not verify target identity",
            self.win.circuit_panel.hex_summary_lbl.text(),
        )
        capture_window(self.win, "hex-inspector-dark.png")

    def test_dialogs_instantiation(self):
        dlg_flash = FlashArduinoDialog(self.win.settings, self.win.lane, self.win)
        dlg_flash.close()

        items = build_dynamic_preflight(lookup("pic12f675"), "nano_new")
        dlg_pre = PreflightDialog(items, "Hardware Safety Checklist — PIC12F675", "Arduino Nano -> ZIF-18 JP3=2-3", self.win)
        dlg_pre.close()

        dlg_set = SettingsDialog(self.win.settings, self.win)
        dlg_set.close()

        dlg_about = AboutDialog(self.win)
        dlg_about.close()

    def test_theme_switching(self):
        self.win.settings.theme = "light"
        self.win.apply_theme("light", 10)
        self.assertEqual(self.win.settings.theme, "light")
        capture_window(self.win, "main-light-no-hardware.png")
        self.win.settings.theme = "dark"
        self.win.apply_theme("dark", 10)

    def test_circuit_drawer_integration(self):
        # Ensure circuit drawer produces valid SVG for the panel
        dev = lookup("pic16f84a")
        board_key = "uno"
        self.win.cmb_board.setCurrentIndex(self.win.cmb_board.findData(board_key))
        self.win.cmb_mcu.setCurrentIndex(self.win.cmb_mcu.findData(dev.name))
        self.win._sync_inspector()
        self.assertIsNotNone(self.win.circuit_panel.schem_view._svg_bytes)
        self.assertTrue(len(self.win.circuit_panel.schem_view._svg_bytes) > 0)

if __name__ == "__main__":
    unittest.main()
