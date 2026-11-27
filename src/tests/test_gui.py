import os
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

# Use Qt's offscreen platform in CI unless the caller explicitly selected one.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QToolBar
from PySide6.QtTest import QTest
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
            "COM4: no ProgramPic response after 10 seconds at 9600 baud.",
        )
        self.assertIn("install firmware", message.lower())
        self.assertIn("9600", message)

    def test_main_window_initialization(self):
        self.assertEqual(self.win.settings.theme, "dark")
        self.assertEqual(self.win.settings.baud, 9600)
        self.assertFalse(self.win.brand_icon.pixmap().isNull())
        self.assertFalse(self.win.log_dock.isVisible())
        self.assertIsNone(self.win.findChild(QToolBar, "mainToolbar"))
        self.assertEqual(self.win.circuit_panel.tabs.count(), 1)
        self.assertEqual(self.win.circuit_panel.tabs.tabText(0), "Circuit Reference")
        self.assertFalse(self.win.circuit_panel.reference_view.image.isNull())
        self.assertFalse(self.win.progress.isVisible())
        self.assertFalse(self.win.btn_cancel.isVisible())
        self.assertIsNotNone(self.win.circuit_panel)
        self.assertIsNotNone(self.win.log_pane)
        self.assertIsNotNone(self.win.cmb_board)
        self.assertIsNotNone(self.win.cmb_mcu)
        self.assertEqual(self.win.status_lbl.text(), "Idle")
        self.assertIn("model", self.win.btn_detect.toolTip())
        self.assertEqual(self.win.btn_erase.toolTip(), "Connect the programmer first.")
        self.assertIn("PIC:", self.win.chip_target.toolTip())
        self.win.cmb_port.clear()
        self.win.cmb_port.addItem("No serial ports detected", "")
        self.win._refresh_actions()
        self.assertFalse(self.win.btn_connect.isEnabled())
        self.assertEqual(self.win.btn_rescan.objectName(), "primary")
        self.assertIn("No port found", self.win.lbl_connection_guidance.text())
        self.assertFalse(self.win.target_tools_panel.isVisible())
        capture_window(self.win, "main-dark-no-hardware.png")

    def test_compact_window_keeps_status_and_workbench_visible(self):
        self.win.resize(1000, 620)
        QApplication.processEvents()
        self.assertEqual(self.win.minimumSize().width(), 1000)
        for chip in (self.win.chip_prog, self.win.chip_target):
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

    def test_circuit_reference_is_the_only_diagram_and_table_follows_it(self):
        panel = self.win.circuit_panel
        self.assertEqual(panel.tabs.count(), 1)
        self.assertEqual(panel.tabs.tabText(0), "Circuit Reference")
        self.assertFalse(panel.reference_view.image.isNull())
        self.assertGreater(panel.wiring_table.rowCount(), 0)
        self.assertEqual(panel.wiring_table.accessibleName(), "Point-to-point hardware connections")
        panel.reference_view.zoom_in()
        panel.reference_view.zoom_fit()

    def test_hex_image_integration(self):
        img = HexImage()
        for i in range(64):
            w = 0x3000 | (i & 0xFF)
            img.data[i * 2] = w & 0xFF
            img.data[i * 2 + 1] = (w >> 8) & 0xFF
        # Include the PIC16F84A config word so this fixture has no missing-fuse warning.
        img.data[0x400E] = 0xFF
        img.data[0x400F] = 0x3F
        self.win.hex_img = img
        self.win.hex_path = "/demo/blink_pic16f84a.hex"
        self.win.session.state.verified = True
        self.win.session.state.port = "COM1"
        self.win._refresh_hex_summary()
        self.win._refresh_actions()
        self.assertTrue(self.win.btn_program.isEnabled())
        self.assertEqual(self.win.btn_program.objectName(), "primary")
        self.assertIn("Loaded:", self.win.lbl_hex_name.text())
        self.assertIn("HEX fits", self.win.lbl_hex_guidance.text())
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
        self.assertEqual(self.win.btn_open_hex.objectName(), "primary")
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
        self.assertIn("last detected PIC12F675", self.win.lbl_target_guidance.text())

    def test_close_defers_until_active_hardware_worker_exits(self):
        started = threading.Event()
        release_worker = threading.Event()

        def blocking_operation(_progress, _percent, _cancel):
            started.set()
            release_worker.wait(timeout=3)
            return "finished safely"

        with patch("gui.main_window.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            self.win._run_task(blocking_operation, lambda _result: None, "Test hardware operation")
            worker = self.win.lane.current
            self.assertIsNotNone(worker)
            self.assertTrue(started.wait(timeout=1))
            self.win.close()
            self.assertTrue(self.win._closing_after_operation)
            self.assertTrue(self.win.isVisible())
            release_worker.set()
            self.assertTrue(worker.wait(5000))
            QApplication.processEvents()
            QTest.qWait(25)

        self.assertFalse(self.win._closing_after_operation)
        self.assertFalse(self.win.lane.busy)
        self.assertFalse(self.win.isVisible())

    def test_worker_error_is_diagnostic_and_restores_ui_state(self):
        def fail_operation(_progress, _percent, _cancel):
            raise RuntimeError("simulated serial failure")

        with patch("gui.main_window.show_diagnostic_error"):
            self.win._run_task(fail_operation, lambda _result: None, "Test operation")
            worker = self.win.lane.current
            self.assertIsNotNone(worker)
            self.assertTrue(worker.wait(5000))
            QApplication.processEvents()

        self.assertFalse(self.win.lane.busy)
        self.assertFalse(self.win.progress.isVisible())
        text = self.win.log_pane.text()
        self.assertIn("simulated serial failure", text)
        self.assertIn("Diagnostic ID:", text)
        self.assertIn("Full log:", text)

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
        self.assertIn("upload completed", dlg_flash.status.text().lower())
        dlg_flash.close()

    def test_flash_dialog_uses_current_board_and_explains_baud_distinction(self):
        # The main workbench selection is authoritative; a stale saved setting
        # must not make the modal claim a different Nano bootloader.
        self.win.settings.board_key = "nano_old"
        dlg_flash = FlashArduinoDialog(
            self.win.settings, self.win.lane, self.win, board_key="nano_new"
        )
        self.assertEqual(dlg_flash.board.currentData(), "nano_new")
        note = dlg_flash.findChild(QLabel)
        self.assertIsNotNone(note)
        self.assertIn("115200 first", note.text())
        self.assertIn("9600 baud", note.text())
        dlg_flash.close()

    def test_main_firmware_dialog_receives_current_nano_selection(self):
        self.win.cmb_board.setCurrentIndex(self.win.cmb_board.findData("nano_new"))
        self.win.settings.board_key = "nano_old"  # Simulate stale persisted UI state.
        with patch("gui.main_window.FlashArduinoDialog") as dialog_type:
            dialog_type.return_value.exec.return_value = 0
            self.win._flash_arduino()
        self.assertEqual(dialog_type.call_args.kwargs["board_key"], "nano_new")
        self.assertEqual(self.win.settings.board_key, "nano_new")

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

    def test_preflight_checklist_wraps_text_and_requires_every_confirmation(self):
        items = build_dynamic_preflight(lookup("pic16f84a"), "nano_new")
        dialog = PreflightDialog(items, "Hardware preflight", "Check the physical setup", self.win)
        self.assertFalse(dialog.continue_button.isEnabled())
        self.assertEqual(len(dialog.check_labels), len(items))
        self.assertTrue(all(label.wordWrap() for label in dialog.check_labels))
        self.assertIn("0 of", dialog.check_summary.text())
        dialog.show()
        QApplication.processEvents()

        QTest.mouseClick(dialog.check_labels[0], Qt.MouseButton.LeftButton)
        self.assertTrue(dialog.checks[0].isChecked())
        for checkbox in dialog.checks[1:]:
            checkbox.setChecked(True)
        self.assertTrue(dialog.continue_button.isEnabled())
        dialog.checks[0].setChecked(False)
        self.assertFalse(dialog.continue_button.isEnabled())
        dialog.close()

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

        self.win.settings.theme = "high_contrast"
        self.win.apply_theme("high_contrast", self.win.settings.font_size)
        self.assertEqual(self.win.circuit_panel._theme, "high_contrast")
        self.assertFalse(self.win.circuit_panel.reference_view.image.isNull())
        capture_window(self.win, "main-high-contrast-no-hardware.png")

        self.win.settings.theme = "dark"
        self.win.apply_theme("dark", self.win.settings.font_size)

    def test_primary_controls_have_clear_accessible_names(self):
        expected = {
            self.win.btn_connect: "Connect programmer",
            self.win.btn_detect: "Detect PIC target",
            self.win.btn_open_hex: "Open HEX file",
            self.win.btn_program: "Program PIC from selected HEX file",
            self.win.btn_verify: "Verify PIC against selected HEX file",
            self.win.status_lbl: "Operation status",
            self.win.progress: "Operation progress",
            self.win.circuit_panel.tabs: "Circuit reference",
        }
        for widget, name in expected.items():
            with self.subTest(name=name):
                self.assertEqual(widget.accessibleName(), name)

    def test_circuit_reference_uses_the_supplied_png(self):
        dev = lookup("pic16f84a")
        self.win.cmb_board.setCurrentIndex(self.win.cmb_board.findData("uno"))
        self.win.cmb_mcu.setCurrentIndex(self.win.cmb_mcu.findData(dev.name))
        self.win._sync_inspector()
        reference = self.win.circuit_panel.reference_view
        image_bytes = reference.image_bytes
        self.assertTrue(image_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(reference.image.width(), 3570)
        self.assertEqual(
            image_bytes,
            (Path(__file__).resolve().parents[2] / "assets" / "reference" / "circuit-reference.png").read_bytes(),
        )
        self.assertFalse(reference.image.isNull())
        self.assertIn("unverified", self.win.circuit_panel.reference_notice.text().lower())

if __name__ == "__main__":
    unittest.main()
