"""About dialog with upstream protocol attribution."""
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout
from app import APP_NAME, GITHUB_URL, VERSION


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.resize(420, 240)
        layout = QVBoxLayout(self)
        label = QLabel(
            f"<h2>{APP_NAME}</h2><p>Version {VERSION}</p>"
            "<p>Arduino PIC programmer front-end using the GPL-3.0 ArdPicProg / ProgramPic protocol.</p>"
            f'<p><a href="{GITHUB_URL}">{GITHUB_URL}</a></p>'
            "<p>High-voltage programming requires careful wiring and the exact target datasheet.</p>"
        )
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)
        layout.addWidget(label)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
