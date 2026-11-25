"""Compact Qt stylesheet and shared palette tokens."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeTokens:
    name: str
    bg: str
    surface: str
    raised: str
    text: str
    subtext: str
    border: str
    accent: str
    success: str
    danger: str


def tokens_for(theme: str) -> ThemeTokens:
    if theme == "light":
        return ThemeTokens("light", "#f3f6fa", "#ffffff", "#e9eff6", "#17212e",
                           "#536579", "#cbd5e1", "#1769aa", "#16825d", "#bd2c2c")
    return ThemeTokens("dark", "#101722", "#182231", "#202d3f", "#edf3fa",
                       "#a8b7c8", "#394b60", "#54a8ff", "#3ac99a", "#ff7272")


def build_qss(t: ThemeTokens, font_size: int = 10) -> str:
    return f"""
    QWidget {{ background-color: {t.bg}; color: {t.text}; font-family: 'Segoe UI', sans-serif; font-size: {font_size}pt; }}
    QMainWindow, QDialog {{ background-color: {t.bg}; }}
    QFrame#headerBar, QFrame#sectionCard, QFrame#calloutCard, QFrame#referenceCard {{ background-color: {t.surface}; border: 1px solid {t.border}; border-radius: 10px; }}
    QFrame#sectionCard {{ padding: 4px; }}
    QLabel#appTitle {{ font-size: {font_size + 5}pt; font-weight: 700; }}
    QLabel#cardTitle {{ font-size: {font_size + 1}pt; font-weight: 650; }}
    QLabel#muted, QLabel#subtext {{ color: {t.subtext}; }}
    QLabel#stepNum, QLabel#modeBadge {{ background: {t.raised}; border: 1px solid {t.border}; border-radius: 6px; padding: 3px; font-weight: 700; }}
    QLabel#chip {{ background: {t.raised}; border: 1px solid {t.border}; border-radius: 10px; padding: 4px 8px; }}
    QPushButton {{ background: {t.raised}; border: 1px solid {t.border}; border-radius: 6px; padding: 6px 10px; }}
    QPushButton:hover {{ border-color: {t.accent}; }}
    QPushButton:disabled {{ color: {t.subtext}; }}
    QPushButton#primary {{ background: {t.accent}; color: white; font-weight: 700; }}
    QPushButton#dangerOutline {{ color: {t.danger}; }}
    QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextBrowser, QTableWidget {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 5px; padding: 4px; selection-background-color: {t.accent}; }}
    QProgressBar {{ background: {t.raised}; border: 1px solid {t.border}; border-radius: 5px; text-align: center; }}
    QProgressBar::chunk {{ background: {t.accent}; border-radius: 4px; }}
    QHeaderView::section {{ background: {t.raised}; padding: 4px; border: 0; }}
    QDockWidget::title {{ background: {t.surface}; padding: 5px; }}
    QToolBar {{ background: {t.surface}; border: 0; spacing: 4px; padding: 4px; }}
    QScrollBar:vertical {{ width: 12px; background: {t.bg}; }}
    QScrollBar::handle:vertical {{ background: {t.border}; border-radius: 5px; min-height: 24px; }}
    """
