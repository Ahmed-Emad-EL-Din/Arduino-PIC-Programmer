import os
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

# Use Qt's offscreen platform in CI unless the caller explicitly selected one.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox, QToolBar
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
        self.win.apply_theme("dark", self.win.settings.font_size)
        self.win._toggle_log(False)
        self.win.show()

    def tearDown(self):
        self.win.close()

    def test_ch340_handshake_failure_has_actionable_firmware_guidance(self):
        message = MainWindow._actionable_operation_error(
            "Connect Programmer",
            "COM4: no ProgramPic response after 10 seconds at 115200 baud.",
        )
        self.assertIn("Install Firmware", message)
        self.assertIn("matching new/old bootloader", message)
        self.assertIn("CH340/CH341", message)
        self.assertIn("115200", message)

    def test_main_window_initialization(self):
        self.assertEqual(self.win.settings.theme, "dark")
        self.assertFalse(self.win.brand_icon.pixmap().isNull())
        self.assertFalse(self.win.log_dock.isVisible())
        toolbar = self.win.findChild(QToolBar, "mainToolbar")
        self.assertIsNotNone(toolbar)
        toolbar_actions = [action.text() for action in toolbar.actions() if not action.isSeparator()]
        self.assertEqual(toolbar_actions, ["Open HEX…", "&Connect Programmer", "Program PIC…"])
        self.assertFalse(self.win.progress.isVisible())
        self.assertFalse(self.win.btn_cancel.isVisible())
        self.assertIsNotNone(self.win.circuit_panel)
        self.assertIsNotNone(self.win.log_pane)
        self.assertIsNotNone(self.win.cmb_board)
        self.assertIsNotNone(self.win.cmb_mcu)
        self.assertIn("not measured", self.win.status_lbl.text())
        self.assertIn("Raw silicon ID", self.win.btn_detect.toolTip())
        self.assertEqual(self.win.btn_erase.toolTip(), "Connect the programmer first.")
        self.assertIn("Target selected:", self.win.chip_target.toolTip())
        self.win.cmb_port.clear()
        self.win.cmb_port.addItem("No serial ports detected", "")
        self.win._refresh_actions()
        self.assertFalse(self.win.btn_connect.isEnabled())
        self.assertEqual(self.win.btn_rescan.objectName(), "primary")
        self.assertIn("No serial port found", self.win.lbl_connection_guidance.text())
        self.assertFalse(self.win.target_tools_panel.isVisible())
        capture_window(self.win, "main-dark-no-hardware.png")

    def test_compact_window_keeps_status_and_workbench_visible(self):
        self.win.resize(1000, 620)
        QApplication.processEvents()
        self.assertEqual(self.win.minimumSize().width(), 1000)
        for chip in (
            self.win.chip_board, self.win.chip_prog,
            self.win.chip_target, self.win.chip_file,
        ):
            self.assertTrue(chip.text())
            self.assertTrue(chip.toolTip())
        self.assertTrue(self.win.circuit_panel.isVisible())
        capture_window(self.win, "main-compact-no-hardware.png")

    def test_activity_log_close_button_persists_hidden_state(self):
        self.win._toggle_log(True)
        QApplication.processEvents()
        self.assertTrue(self.win.act_log.isChecked())
        self.win.log_dock.hide()
        QApplication.processEvents()
        self.assertFalse(self.win.act_log.isChecked())
        self.assertFalse(self.win.settings.log_visible)

    def test_busy_serial_port_error_has_recovery_steps(self):
        message = MainWindow._actionable_operation_error(
            "Connect Programmer", "ser_open(): can't open device COM5: Access is denied."
        )
        self.assertIn("Close Arduino Serial Monitor", message)
        self.assertIn("select Rescan", message)

    def test_connection_controls_follow_connection_state(self):
        self.win.session.state.verified = True
        self.win.session.state.port = "COM1"
        self.win._refresh_actions()
        self.assertFalse(self.win.btn_connect.isVisible())
        self.assertTrue(self.win.btn_disconnect.isVisible())
        self.assertFalse(self.win.btn_flash_ard.isVisible())
        self.assertEqual(self.win.btn_open_hex.objectName(), "primary")

    def test_optional_target_actions_expand_on_request(self):
        self.assertFalse(self.win.target_tools_panel.isVisible())
        self.win.btn_more_target.click()
        self.assertTrue(self.win.target_tools_panel.isVisible())
        self.assertEqual(self.win.btn_more_target.accessibleName(), "Hide more target actions")

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
        self.win.session.state.verified = True
        self.win.session.state.port = "COM1"
        self.win._refresh_hex_summary()
        self.win._refresh_actions()
        self.assertTrue(self.win.btn_program.isEnabled())
        self.assertEqual(self.win.btn_program.objectName(), "primary")
        self.win.circuit_panel.set_hex_image(img)
        self.win.circuit_panel.tabs.setCurrentIndex(2)
        self.assertIn(
            "does not verify target identity",
            self.win.circuit_panel.hex_summary_lbl.text(),
        )
        self.assertIn("Addresses fit", self.win.lbl_hex_guidance.text())
        self.assertIn("does not verify target identity", self.win.lbl_hex_guidance.text())
        capture_window(self.win, "hex-inspector-dark.png")

    def test_out_of_range_hex_disables_program_when_connected(self):
        self.win.session.state.verified = True
        self.win.session.state.port = "COM1"
        img = HexImage()
        img.data[0x6000] = 0x34
        img.data[0x6001] = 0x12
        self.win.hex_img = img
        self.win.hex_path = "out-of-range.hex"
        self.win._refresh_hex_summary()
        self.win._refresh_actions()
        self.assertFalse(self.win.btn_program.isEnabled())
        self.assertFalse(self.win.btn_verify.isEnabled())
        self.assertEqual(self.win.btn_inspect_hex.objectName(), "primary")
        self.assertIn("outside", self.win.btn_program.toolTip())

    def test_reported_target_mismatch_blocks_hardware_actions(self):
        self.win.session.state.verified = True
        self.win.session.state.port = "COM1"
        self.win.cmb_mcu.setCurrentIndex(self.win.cmb_mcu.findData("pic16f84a"))
        self.win._reported_target_name = "pic12f675"
        self.win.hex_img = HexImage()
        self.win.hex_img.data[0] = 0
        self.win.hex_img.data[1] = 0
        self.win._refresh_hex_summary()
        self.win._refresh_actions()
        self.assertFalse(self.win.btn_blank.isEnabled())
        self.assertFalse(self.win.btn_read.isEnabled())
        self.assertFalse(self.win.btn_erase.isEnabled())
        self.assertFalse(self.win.btn_program.isEnabled())
        self.assertTrue(self.win.btn_detect.isEnabled())
        self.assertEqual(self.win.btn_detect.objectName(), "primary")
        self.assertIn("Blocked:", self.win.lbl_target_guidance.text())

    def test_firmware_upload_runs_off_the_gui_thread_and_keeps_dialog_alive(self):
        dlg_flash = FlashArduinoDialog(self.win.settings, None, self.win)
        dlg_flash.board.setCurrentIndex(dlg_flash.board.findData("nano_new"))
        dlg_flash.port.clear()
        dlg_flash.port.addItem("USB-SERIAL CH340 (COM4)", "COM4")
        release_upload = threading.Event()
        flashed = []
        dlg_flash.flashed.connect(lambda port, board: flashed.append((port, board)))

        def fake_upload(_board, _port):
            release_upload.wait(timeout=3)
            return "avrdude: done"

        with patch("gui.dialogs.flash_arduino.QMessageBox.warning", return_value=QMessageBox.StandardButton.Yes), \
             patch("gui.dialogs.flash_arduino.QMessageBox.information"), \
             patch("gui.dialogs.flash_arduino.flash_firmware", side_effect=fake_upload):
            dlg_flash._flash()
            worker = dlg_flash._worker
            self.assertIsNotNone(worker)
            self.assertTrue(worker.isRunning())
            self.assertFalse(dlg_flash.flash_button.isEnabled())
            self.assertFalse(dlg_flash.close_button.isEnabled())
            release_upload.set()
            self.assertTrue(worker.wait(5000))
            QApplication.processEvents()

        self.assertFalse(dlg_flash._uploading)
        self.assertEqual(flashed, [("COM4", "nano_new")])
        self.assertIn("uploaded", dlg_flash.status.text().lower())
        dlg_flash.close()

    def test_flash_dialog_explains_unsupported_bootloader_uploads(self):
        dlg_flash = FlashArduinoDialog(self.win.settings, self.win.lane, self.win)
        dlg_flash.board.setCurrentIndex(dlg_flash.board.findData("uno"))
        self.assertTrue(dlg_flash.flash_button.isEnabled())
        dlg_flash.board.setCurrentIndex(dlg_flash.board.findData("leonardo"))
        self.assertFalse(dlg_flash.flash_button.isEnabled())
        self.assertIn("Use Arduino IDE", dlg_flash.board_note.text())
        dlg_flash.board.setCurrentIndex(dlg_flash.board.findData("uno"))
        self.assertTrue(dlg_flash.flash_button.isEnabled())
        self.assertTrue(dlg_flash.board_note.isHidden())
        dlg_flash.close()

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
        self.win.apply_theme("dark", self.win.settings.font_size)

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
