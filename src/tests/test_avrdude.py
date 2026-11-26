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
            output = flash_firmware("nano_new", "COM4")

        args = run.call_args.args[0]
        self.assertIn("COM4", args)
        self.assertEqual(args[args.index("-P") + 1], "COM4")
        self.assertEqual(args[args.index("-b") + 1], "115200")
        self.assertEqual(run.call_args.kwargs["timeout"], 180)
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(run.call_args.kwargs["errors"], "replace")
        self.assertIn("avrdude: done", output)

    def test_old_nano_bootloader_uses_57600(self):
        result = SimpleNamespace(returncode=0, stdout="", stderr="upload complete")
        with patch("core.avrdude._resource_root", return_value=self.root), \
             patch("core.avrdude.subprocess.run", return_value=result) as run:
            flash_firmware("nano_old", "COM12")
        args = run.call_args.args[0]
        self.assertEqual(args[args.index("-P") + 1], "COM12")
        self.assertEqual(args[args.index("-b") + 1], "57600")

    def test_avrdude_failure_is_reported_without_crashing_the_caller(self):
        result = SimpleNamespace(returncode=1, stdout="", stderr="not in sync")
        with patch("core.avrdude._resource_root", return_value=self.root), \
             patch("core.avrdude.subprocess.run", return_value=result):
            with self.assertRaisesRegex(FlashError, "not in sync"):
                flash_firmware("nano_new", "COM4")

    def test_avrdude_timeout_becomes_a_user_facing_flash_error(self):
        timeout = subprocess.TimeoutExpired("avrdude", 180)
        with patch("core.avrdude._resource_root", return_value=self.root), \
             patch("core.avrdude.subprocess.run", side_effect=timeout):
            with self.assertRaisesRegex(FlashError, "Could not run avrdude"):
                flash_firmware("nano_new", "COM4")


if __name__ == "__main__":
    unittest.main()
