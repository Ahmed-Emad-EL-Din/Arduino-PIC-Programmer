import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.avrdude import FlashError, flash_firmware


class TestFirmwareUpload(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        tools = self.root / "tools" / "avrdude"
        tools.mkdir(parents=True)
        (tools / "avrdude.exe").write_bytes(b"fake avrdude")
        (tools / "avrdude.conf").write_text("# test config", encoding="ascii")
        firmware = self.root / "firmware" / "precompiled"
        firmware.mkdir(parents=True)
        (firmware / "nano_new.hex").write_text(":00000001FF\n", encoding="ascii")
        (firmware / "nano_old.hex").write_text(":00000001FF\n", encoding="ascii")

    def test_ch340_com_port_uses_selected_nano_bootloader_settings(self):
        result = SimpleNamespace(returncode=0, stdout="avrdude: done", stderr="")
        with patch("core.avrdude._resource_root", return_value=self.root), \
             patch("core.avrdude.subprocess.run", return_value=result) as run:
            outcome = flash_firmware("nano_new", "COM4")

        args = run.call_args.args[0]
        self.assertEqual(args[args.index("-P") + 1], "COM4")
        self.assertEqual(args[args.index("-b") + 1], "115200")
        self.assertEqual(run.call_args.kwargs["timeout"], 180)
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(run.call_args.kwargs["errors"], "replace")
        self.assertIn("avrdude: done", outcome.output)
        self.assertEqual(outcome.baud, 115200)
        self.assertEqual(outcome.board_key, "nano_new")
        self.assertFalse(outcome.fallback_used)

    def test_old_nano_bootloader_tries_115200_first(self):
        result = SimpleNamespace(returncode=0, stdout="", stderr="upload complete")
        with patch("core.avrdude._resource_root", return_value=self.root), \
             patch("core.avrdude.subprocess.run", return_value=result) as run:
            outcome = flash_firmware("nano_old", "COM12")
        args = run.call_args.args[0]
        self.assertEqual(args[args.index("-P") + 1], "COM12")
        self.assertEqual(args[args.index("-b") + 1], "115200")
        self.assertEqual(outcome.board_key, "nano_new")
        self.assertEqual(outcome.baud, 115200)
        self.assertFalse(outcome.fallback_used)

    def test_nano_upload_retries_the_other_bootloader_baud_after_sync_failure(self):
        first = SimpleNamespace(returncode=1, stdout="", stderr="stk500_getsync: not in sync")
        retry = SimpleNamespace(returncode=0, stdout="avrdude: done", stderr="")
        with patch("core.avrdude._resource_root", return_value=self.root), \
             patch("core.avrdude.subprocess.run", side_effect=[first, retry]) as run:
            outcome = flash_firmware("nano_old", "COM4")

        self.assertEqual(run.call_count, 2)
        first_args = run.call_args_list[0].args[0]
        retry_args = run.call_args_list[1].args[0]
        self.assertEqual(first_args[first_args.index("-b") + 1], "115200")
        self.assertEqual(retry_args[retry_args.index("-b") + 1], "57600")
        self.assertEqual(outcome.board_key, "nano_old")
        self.assertEqual(outcome.baud, 57600)
        self.assertTrue(outcome.fallback_used)
        self.assertIn("succeeded using the alternate 57600-baud", outcome.output)

    def test_both_nano_speeds_are_included_in_copyable_failure_details(self):
        first = SimpleNamespace(returncode=1, stdout="", stderr="not in sync at 115200")
        retry = SimpleNamespace(returncode=1, stdout="", stderr="not in sync at 57600")
        with patch("core.avrdude._resource_root", return_value=self.root), \
             patch("core.avrdude.subprocess.run", side_effect=[first, retry]):
            with self.assertRaises(FlashError) as caught:
                flash_firmware("nano_old", "COM4")
        message = str(caught.exception)
        self.assertIn("115200 and 57600 baud", message)
        self.assertIn("Attempt at 115200 baud", message)
        self.assertIn("not in sync at 115200", message)
        self.assertIn("not in sync at 57600", message)

    def test_non_sync_avrdude_failure_is_reported(self):
        result = SimpleNamespace(returncode=1, stdout="", stderr="COM4 access denied")
        with patch("core.avrdude._resource_root", return_value=self.root), \
             patch("core.avrdude.subprocess.run", return_value=result) as run:
            with self.assertRaisesRegex(FlashError, "COM4 access denied"):
                flash_firmware("nano_new", "COM4")
        run.assert_called_once()

    def test_avrdude_timeout_becomes_a_user_facing_flash_error(self):
        timeout = subprocess.TimeoutExpired("avrdude", 180)
        with patch("core.avrdude._resource_root", return_value=self.root), \
             patch("core.avrdude.subprocess.run", side_effect=timeout):
            with self.assertRaisesRegex(FlashError, "Could not run avrdude"):
                flash_firmware("nano_new", "COM4")


if __name__ == "__main__":
    unittest.main()
