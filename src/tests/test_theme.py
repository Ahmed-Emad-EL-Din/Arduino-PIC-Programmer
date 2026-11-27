import unittest

from gui.theme import build_qss, tokens_for


def _luminance(color: str) -> float:
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def _contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


class ThemeTests(unittest.TestCase):
    def test_text_and_status_colors_meet_wcag_aa_contrast(self):
        for theme in ("dark", "light", "high_contrast"):
            with self.subTest(theme=theme):
                palette = tokens_for(theme)
                for foreground in ("text", "subtext"):
                    for background in ("bg", "surface", "raised"):
                        self.assertGreaterEqual(
                            _contrast_ratio(getattr(palette, foreground), getattr(palette, background)),
                            4.5,
                            f"{theme}: {foreground} on {background}",
                        )
                for foreground, background in (
                    ("success", "surface"),
                    ("danger", "surface"),
                    ("warning", "warning_surface"),
                    ("on_accent", "accent"),
                ):
                    self.assertGreaterEqual(
                        _contrast_ratio(getattr(palette, foreground), getattr(palette, background)),
                        4.5,
                        f"{theme}: {foreground} on {background}",
                    )

    def test_high_contrast_appearance_uses_black_white_and_yellow(self):
        palette = tokens_for("high_contrast")
        self.assertEqual(palette.bg, "#000000")
        self.assertEqual(palette.text, "#ffffff")
        self.assertEqual(palette.accent, "#ffff00")
        self.assertEqual(palette.on_accent, "#000000")

    def test_keyboard_focus_rules_cover_common_interactive_controls(self):
        qss = build_qss(tokens_for("high_contrast"))
        for selector in (
            "QPushButton:focus",
            "QToolButton:focus",
            "QComboBox:focus",
            "QCheckBox:focus",
            "QTabBar::tab:focus",
            "QPlainTextEdit:focus",
            "QTableWidget:focus",
        ):
            with self.subTest(selector=selector):
                self.assertIn(selector, qss)
        self.assertIn("border: 2px solid #ffff00", qss)
        self.assertIn("padding: 8px 12px", qss)


if __name__ == "__main__":
    unittest.main()
