import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QLabel

from gui.startup_splash import StartupSplash


ROOT = Path(__file__).resolve().parents[2]


class TestStartupSplash(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_splash_centers_logo_and_displays_requested_credit(self):
        splash = StartupSplash(ROOT / "assets" / "app-icon.png")
        self.assertEqual(splash.size().width(), StartupSplash.WIDTH)
        self.assertEqual(splash.size().height(), StartupSplash.HEIGHT)
        logo = splash.findChild(QLabel, "splashLogo")
        credit = splash.findChild(QLabel, "splashCredit")
        self.assertIsNotNone(logo)
        self.assertFalse(logo.pixmap().isNull())
        self.assertEqual(credit.text(), "Made By: Ahmed Emad")

        screen = QGuiApplication.primaryScreen()
        self.assertIsNotNone(screen)
        available = screen.availableGeometry()
        splash.show_centered()
        self.app.processEvents()
        self.assertEqual(
            splash.geometry().center(), available.center(),
        )
        splash.close()


if __name__ == "__main__":
    unittest.main()
