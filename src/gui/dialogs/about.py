"""About dialog with upstream protocol attribution."""
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QWidget
from app import APP_NAME, GITHUB_URL, VERSION
from .scrollable import fit_dialog_to_screen, scrollable_content


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        content = QWidget()
        content_layout = QVBoxLayout(content)
        label = QLabel(
            f"<h2>{APP_NAME}</h2><p>Version {VERSION}</p>"
            "<p>Arduino PIC programmer front-end using the GPL-3.0 ArdPicProg / ProgramPic protocol.</p>"
            f'<p><a href="{GITHUB_URL}">{GITHUB_URL}</a></p>'
            "<p>High-voltage programming requires careful wiring and the exact target datasheet.</p>"
        )
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)
        content_layout.addWidget(label)
        layout = QVBoxLayout(self)
        layout.addWidget(scrollable_content(content), 1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        fit_dialog_to_screen(self, 520, 420, 360, 260)
