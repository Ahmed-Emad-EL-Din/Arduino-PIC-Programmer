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
    warning: str
    warning_surface: str
    accent_hover: str
    on_accent: str


def tokens_for(theme: str) -> ThemeTokens:
    """Return a restrained, high-contrast palette for the selected appearance."""
    if theme == "light":
        return ThemeTokens(
            "light", "#f3f6fa", "#ffffff", "#e9eff6", "#17212e",
            "#536579", "#cbd5e1", "#175ea8", "#16734f", "#b4232d",
            "#825b00", "#fff6df", "#124f8d", "#ffffff",
        )
    if theme == "high_contrast":
        return ThemeTokens(
            "high_contrast", "#000000", "#000000", "#000000", "#ffffff",
            "#ffffff", "#ffffff", "#ffff00", "#00ff00", "#ff6b6b",
            "#ffff00", "#000000", "#ffffff", "#000000",
        )
    return ThemeTokens(
        "dark", "#101722", "#182231", "#202d3f", "#edf3fa",
        "#a8b7c8", "#394b60", "#3478c7", "#3ac99a", "#ff7272",
        "#f0bd62", "#302817", "#2867ad", "#ffffff",
    )


def build_qss(t: ThemeTokens, font_size: int = 10) -> str:
    return f"""
    QWidget {{ background-color: {t.bg}; color: {t.text}; font-family: 'Segoe UI', sans-serif; font-size: {font_size}pt; }}
    QMainWindow, QDialog {{ background-color: {t.bg}; }}
    QFrame#headerBar, QFrame#sectionCard, QFrame#calloutCard, QFrame#referenceCard {{ background-color: {t.surface}; border: 1px solid {t.border}; border-radius: 8px; }}
    QFrame#sectionCard {{ padding: 4px; }}
    QFrame#subCard {{ background-color: {t.raised}; border: 1px solid {t.border}; border-radius: 6px; }}
    QLabel#brandIcon {{ background: transparent; border: 0; }}
    QLabel#appTitle {{ font-size: {font_size + 5}pt; font-weight: 700; }}
    QLabel#cardTitle {{ font-size: {font_size + 1}pt; font-weight: 650; }}
    QLabel#muted, QLabel#subtext {{ color: {t.subtext}; }}
    QLabel#warn {{ color: {t.warning}; font-weight: 600; }}
    QLabel#monoSmall {{ color: {t.subtext}; font-family: 'Consolas', 'DejaVu Sans Mono', monospace; font-size: {max(8, font_size - 1)}pt; }}
    QLabel#sectionLabel {{ font-weight: 650; }}
    QLabel#stepNum, QLabel#modeBadge {{ background: {t.raised}; border: 1px solid {t.border}; border-radius: 6px; padding: 4px; font-weight: 700; }}
    QLabel#chip {{ background: {t.raised}; border: 1px solid {t.border}; border-radius: 6px; padding: 4px 8px; }}
    QLabel#chipOk {{ color: {t.success}; background: {t.surface}; border: 1px solid {t.success}; border-radius: 6px; padding: 4px 8px; }}
    QLabel#chipWarn {{ color: {t.warning}; background: {t.warning_surface}; border: 1px solid {t.warning}; border-radius: 6px; padding: 4px 8px; }}
    QLabel#chipBad {{ color: {t.danger}; background: {t.surface}; border: 1px solid {t.danger}; border-radius: 6px; padding: 4px 8px; }}
    QLabel#guidance {{ color: {t.subtext}; padding: 4px 8px; }}
    QLabel#guidanceWarn {{ color: {t.warning}; background: {t.warning_surface}; border-left: 4px solid {t.warning}; border-radius: 4px; padding: 8px; }}
    QLabel#guidanceOk {{ color: {t.success}; background: {t.surface}; border-left: 4px solid {t.success}; border-radius: 4px; padding: 8px; }}
    QToolButton#disclosureButton {{ color: {t.accent}; background: transparent; border: 0; padding: 4px; font-weight: 600; }}
    QToolButton#disclosureButton:hover {{ color: {t.accent_hover}; }}
    QFrame#targetToolsPanel {{ background: {t.raised}; border: 1px solid {t.border}; border-radius: 6px; }}
    QPushButton {{ background: {t.raised}; border: 1px solid {t.border}; border-radius: 6px; padding: 8px 12px; min-height: 24px; }}
    QPushButton:hover {{ border-color: {t.accent}; }}
    QPushButton:pressed {{ background: {t.border}; }}
    QPushButton:focus, QToolButton:focus, QComboBox:focus, QLineEdit:focus,
    QSpinBox:focus, QCheckBox:focus, QRadioButton:focus, QTabBar::tab:focus,
    QPlainTextEdit:focus, QTextBrowser:focus, QTableWidget:focus {{ border: 2px solid {t.accent}; }}
    QPushButton:disabled {{ color: {t.subtext}; background: {t.bg}; border-color: {t.border}; }}
    QPushButton#primary {{ background: {t.accent}; color: {t.on_accent}; border-color: {t.accent}; font-weight: 700; }}
    QPushButton#primary:hover {{ background: {t.accent_hover}; border-color: {t.accent_hover}; }}
    QPushButton#primary:disabled {{ color: {t.subtext}; background: {t.raised}; border-color: {t.border}; }}
    QPushButton#dangerOutline {{ color: {t.danger}; }}
    QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextBrowser, QTableWidget {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 5px; padding: 4px; selection-background-color: {t.accent}; selection-color: {t.on_accent}; }}
    QComboBox::drop-down {{ border: 0; width: 24px; }}
    QCheckBox {{ spacing: 10px; }}
    QCheckBox::indicator {{ width: 20px; height: 20px; border: 2px solid {t.border}; border-radius: 4px; background-color: {t.surface}; }}
    QCheckBox::indicator:hover {{ border-color: {t.accent}; }}
    QCheckBox::indicator:checked {{ background-color: {t.accent}; border-color: {t.accent}; }}
    QProgressBar {{ background: {t.raised}; border: 1px solid {t.border}; border-radius: 5px; text-align: center; min-height: 12px; }}
    QProgressBar::chunk {{ background: {t.accent}; border-radius: 4px; }}
    QHeaderView::section {{ background: {t.raised}; color: {t.text}; padding: 8px 10px; border: 0; font-weight: 600; }}
    QTableWidget#wiringTable {{ alternate-background-color: {t.raised}; gridline-color: {t.border}; }}
    QTabWidget::pane {{ border: 1px solid {t.border}; border-radius: 6px; top: -1px; }}
    QTabBar::tab {{ background: {t.raised}; color: {t.subtext}; border: 1px solid {t.border}; border-bottom-color: {t.border}; padding: 9px 16px; min-width: 132px; min-height: 30px; margin-right: 4px; }}
    QTabBar::tab:hover:!selected {{ color: {t.text}; background: {t.surface}; }}
    QTabBar::tab:selected {{ color: {t.text}; background: {t.surface}; border: 1px solid {t.border}; border-bottom: 3px solid {t.accent}; font-weight: 700; }}
    QDockWidget::title {{ background: {t.surface}; padding: 8px; }}
    QToolBar {{ background: {t.surface}; border: 0; spacing: 4px; padding: 4px; }}
    QMenu {{ background: {t.surface}; border: 1px solid {t.border}; }}
    QMenu::item:selected {{ background: {t.raised}; }}
    QToolTip {{ color: {t.text}; background: {t.surface}; border: 1px solid {t.border}; padding: 4px; }}
    QScrollBar:vertical {{ width: 12px; background: {t.bg}; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {t.border}; border-radius: 5px; min-height: 24px; }}
    QScrollBar::handle:vertical:hover {{ background: {t.subtext}; }}
    """
