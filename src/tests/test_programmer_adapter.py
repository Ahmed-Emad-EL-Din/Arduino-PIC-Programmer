import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.ihex import HexImage
from core.mcu_db import DEFAULT_DEVICE
from core.programmer import ProgrammerSession
from core.protocol import ProgrammerState, ProtocolError


class TestProgrammerAdapter(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.host = self.root / "fake_host.py"
        self.host.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib,sys\n"
            "args=sys.argv[1:]\n"
            "if '--list-devices' in args:\n"
            " print('Supported devices:')\n print('* pic16f84a')\n"
            "elif '--detect' in args:\n"
            " print('Device pic16f84a, program memory: 1024 words, data memory: 64 bytes.')\n"
            "elif '--output-hexfile' in args:\n"
            " p=pathlib.Path(args[args.index('--output-hexfile')+1])\n"
            " p.write_text(pathlib.Path(__file__).with_name('readback.hex').read_text())\n"
            "print('')\n",
            encoding="utf-8",
        )
        self.expected = HexImage.from_flat({0: 0x1234, 0x2007: 0x3FFF})
        (self.root / "readback.hex").write_text(self.expected.to_hex(), encoding="ascii")
        self.session = ProgrammerSession(host_path=[sys.executable, str(self.host)])

    def test_connect_and_detect(self):
        state = self.session.connect("FAKEPORT")
        self.assertTrue(state.verified)
        self.assertEqual(state.port, "FAKEPORT")
        self.assertIn("pic16f84a", state.supported)
        info, dev = self.session.detect_chip()
        self.assertEqual(info.device_name, "PIC16F84A")
        self.assertEqual(dev, DEFAULT_DEVICE)

    def test_program_result_does_not_claim_verification_when_disabled(self):
        self.session.state = ProgrammerState(port="FAKEPORT", verified=True)
        with patch.object(self.session, "_checked", return_value="program command completed"), \
             patch.object(self.session, "_readback") as readback:
            result = self.session.program_hex(
                HexImage.from_flat({0: 0x1234}),
                DEFAULT_DEVICE,
                do_verify=False,
            )
        self.assertIn("read-back comparison was disabled and not performed", result)
        readback.assert_not_called()

    def test_program_result_reports_successful_readback_when_enabled(self):
        self.session.state = ProgrammerState(port="FAKEPORT", verified=True)
        image = HexImage.from_flat({0: 0x1234})
        with patch.object(self.session, "_checked", return_value="program command completed"), \
             patch.object(self.session, "_readback", return_value=image):
            result = self.session.program_hex(image, DEFAULT_DEVICE, do_verify=True)
        self.assertIn("read-back comparison passed", result)

    def test_readback_comparison_rejects_mismatch_with_hex_values(self):
        different = HexImage.from_flat({0: 0x1FFF})
        with self.assertRaises(ProtocolError) as raised:
            self.session._compare(self.expected, different, DEFAULT_DEVICE)
        self.assertIn("0x0000: expected 1234, got 1FFF", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
