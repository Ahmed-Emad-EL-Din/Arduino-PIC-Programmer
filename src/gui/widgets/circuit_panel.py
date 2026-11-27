"""Circuit reference image and contextual, point-to-point wiring table."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QImage, QPainter, QWheelEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.mcu_db import DEFAULT_DEVICE, McuDevice, lookup
from core.pinout_db import (
    MODE_ZIF_8,
    MODE_ZIF_18,
    build_wiring_rows,
    get_board_wiring,
    get_pic_wiring,
)


def _assets_reference_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parents[3]
    return base / "assets" / "reference"


class ZoomableImageView(QScrollArea):
    """Zoomable, high-DPI raster image viewer with Ctrl+Wheel and drag-to-pan."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setObjectName("imageScroll")
        self._image_bytes = b""
        self._image = QImage()
        self._zoom = 1.0
        self._fit_mode = True
        self._drag_pos: Optional[QPoint] = None
        self._canvas = _ImageCanvas(self._image, self)
        self.setWidget(self._canvas)
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_image(self, image_bytes: bytes) -> None:
        image = QImage.fromData(image_bytes)
        if image.isNull():
            raise ValueError("The circuit reference image could not be decoded.")
        self._image_bytes = image_bytes
        self._image = image
        self._canvas.set_image(image)
        self._fit_mode = True
        self._update_canvas_size()

    @property
    def image_bytes(self) -> bytes:
        return self._image_bytes

    @property
    def image(self) -> QImage:
        return self._image

    def zoom_in(self) -> None:
        self._fit_mode = False
        self._set_zoom(self._zoom * 1.2)

    def zoom_out(self) -> None:
        self._fit_mode = False
        self._set_zoom(self._zoom / 1.2)

    def zoom_fit(self) -> None:
        self._fit_mode = True
        self._update_canvas_size()

    def _set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.05, min(3.5, zoom))
        self._update_canvas_size()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._fit_mode:
            self._update_canvas_size()

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.position().toPoint()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_pos is not None:
            current = event.position().toPoint()
            delta = current - self._drag_pos
            self._drag_pos = current
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_pos = None
        self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def _update_canvas_size(self) -> None:
        if self._image.isNull():
            return
        viewport = self.viewport().size()
        if self._fit_mode and viewport.width() > 40 and viewport.height() > 40:
            scale = min(
                (viewport.width() - 16) / self._image.width(),
                (viewport.height() - 16) / self._image.height(),
                1.35,
            )
            self._zoom = max(scale, 0.05)
        self._canvas.setFixedSize(
            max(1, int(self._image.width() * self._zoom)),
            max(1, int(self._image.height() * self._zoom)),
        )
        self._canvas.update()


class _ImageCanvas(QWidget):
    def __init__(self, image: QImage, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._image = image
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def set_image(self, image: QImage) -> None:
        self._image = image
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        if self._image.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(self.rect(), self._image)
        painter.end()


class CircuitPanel(QWidget):
    """A single circuit-reference view with the matching wiring table below it."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("inspectorPane")
        self._mcu_name = "pic16f84a"
        self._board_key = "uno"
        self._theme = "dark"

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.banner = QFrame()
        self.banner.setObjectName("calloutCard")
        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)
        banner_layout.setSpacing(12)
        text_column = QVBoxLayout()
        text_column.setSpacing(2)
        self.hw_headline = QLabel()
        self.hw_headline.setObjectName("cardTitle")
        self.hw_headline.setAccessibleName("Selected board and PIC")
        self.hw_subline = QLabel()
        self.hw_subline.setObjectName("muted")
        self.hw_subline.setWordWrap(True)
        text_column.addWidget(self.hw_headline)
        text_column.addWidget(self.hw_subline)
        banner_layout.addLayout(text_column, 1)
        self.mode_badge = QLabel()
        self.mode_badge.setObjectName("modeBadge")
        self.mode_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner_layout.addWidget(self.mode_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(self.banner)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("inspectorTabs")
        self.tabs.setAccessibleName("Circuit reference")
        self._build_reference_tab()
        root.addWidget(self.tabs, 1)
        self.refresh_diagrams()

    def _build_reference_tab(self) -> None:
        page = QWidget()
        page.setObjectName("circuitReferencePage")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(8, 8, 8, 8)
        page_layout.setSpacing(8)

        self.reference_splitter = QSplitter(Qt.Orientation.Vertical)
        self.reference_splitter.setObjectName("referenceAndConnectionsSplitter")
        self.reference_splitter.setHandleWidth(8)
        self.reference_splitter.setChildrenCollapsible(False)

        self.reference_card = QFrame()
        self.reference_card.setObjectName("referenceCard")
        reference_layout = QVBoxLayout(self.reference_card)
        reference_layout.setContentsMargins(12, 10, 12, 10)
        reference_layout.setSpacing(8)

        controls = QHBoxLayout()
        controls.setSpacing(6)
        title = QLabel("Example circuit · PIC16F84A")
        title.setObjectName("cardTitle")
        controls.addWidget(title, 1)
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setAccessibleName("Zoom circuit diagram out")
        self.btn_zoom_out.setToolTip("Zoom out (Ctrl+mouse wheel also works)")
        self.btn_fit = QPushButton("Fit")
        self.btn_fit.setAccessibleName("Fit circuit diagram to view")
        self.btn_fit.setToolTip("Fit the complete drawing in the available panel")
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setAccessibleName("Zoom circuit diagram in")
        self.btn_zoom_in.setToolTip("Zoom in (Ctrl+mouse wheel also works)")
        for button in (self.btn_zoom_out, self.btn_fit, self.btn_zoom_in):
            button.setFixedSize(42, 32)
            controls.addWidget(button)
        self.btn_open_source = QPushButton("Open original PNG")
        self.btn_open_source.setAccessibleName("Open original supplied circuit PNG")
        self.btn_open_source.setToolTip("Open the exact supplied PNG file outside the app")
        controls.addWidget(self.btn_open_source)
        reference_layout.addLayout(controls)

        self.reference_notice = QLabel(
            "Illustration only—not wiring instructions. The supplied PIC16F84A example shows 24 V input and an LM317. "
            "It is unverified and may not match the selected board. Never connect VPP to an Arduino pin; "
            "do not apply 24 V to a shield unless its documentation permits it."
        )
        self.reference_notice.setObjectName("guidanceWarn")
        self.reference_notice.setAccessibleName("Unverified PIC16F84A example circuit safety notice")
        self.reference_notice.setWordWrap(True)
        reference_layout.addWidget(self.reference_notice)

        self.reference_view = ZoomableImageView()
        self.reference_view.setAccessibleName("PIC16F84A example circuit image")
        self.reference_view.setAccessibleDescription(
            "Exact user-supplied, unverified example circuit for PIC16F84A. It is not the selected board's wiring map."
        )
        image_file = _assets_reference_dir() / "circuit-reference.png"
        self.btn_open_source.setEnabled(image_file.is_file())
        self.btn_open_source.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(image_file)))
        )
        self.btn_zoom_out.clicked.connect(self.reference_view.zoom_out)
        self.btn_fit.clicked.connect(self.reference_view.zoom_fit)
        self.btn_zoom_in.clicked.connect(self.reference_view.zoom_in)
        if image_file.is_file():
            try:
                self.reference_view.set_image(image_file.read_bytes())
            except (OSError, ValueError) as exc:
                self.reference_view.setAccessibleDescription(str(exc))
                self.reference_notice.setText(
                    f"The supplied circuit image could not be displayed: {exc} Check the datasheet and hardware guide before wiring."
                )
        else:
            self.reference_notice.setText(
                "The supplied circuit image is missing. Check the datasheet and hardware guide before wiring."
            )
        reference_layout.addWidget(self.reference_view, 1)
        self.reference_splitter.addWidget(self.reference_card)

        self.connections_card = QFrame()
        self.connections_card.setObjectName("referenceCard")
        connections_layout = QVBoxLayout(self.connections_card)
        connections_layout.setContentsMargins(12, 10, 12, 10)
        connections_layout.setSpacing(6)

        heading = QHBoxLayout()
        heading.setSpacing(8)
        table_title = QLabel("Point-to-point connections")
        table_title.setObjectName("cardTitle")
        heading.addWidget(table_title, 1)
        self.connection_count = QLabel()
        self.connection_count.setObjectName("modeBadge")
        self.connection_count.setAccessibleName("Connection row count")
        heading.addWidget(self.connection_count)
        connections_layout.addLayout(heading)

        self.table_note = QLabel(
            "From → To for the selected firmware profile. This table and the example drawing are separate references; verify actual wiring against the board documentation and PIC datasheet."
        )
        self.table_note.setObjectName("muted")
        self.table_note.setWordWrap(True)
        connections_layout.addWidget(self.table_note)

        self.wiring_table = QTableWidget(0, 4)
        self.wiring_table.setObjectName("wiringTable")
        self.wiring_table.setAccessibleName("Point-to-point hardware connections")
        self.wiring_table.setAccessibleDescription(
            "Selected firmware profile, shown as signal and source-to-target connections. Not cross-validated against the example drawing. Verify each connection before wiring."
        )
        self.wiring_table.setHorizontalHeaderLabels(
            ["Signal", "From · board / shield", "To · PIC pin(s)", "Notes / constraints"]
        )
        self.wiring_table.verticalHeader().setVisible(False)
        self.wiring_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.wiring_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.wiring_table.setAlternatingRowColors(True)
        self.wiring_table.setWordWrap(True)
        self.wiring_table.setMinimumHeight(120)
        self.wiring_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        header = self.wiring_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setMinimumSectionSize(84)
        connections_layout.addWidget(self.wiring_table, 1)
        self.reference_splitter.addWidget(self.connections_card)
        self.reference_splitter.setStretchFactor(0, 3)
        self.reference_splitter.setStretchFactor(1, 2)
        self.reference_splitter.setSizes([500, 340])
        page_layout.addWidget(self.reference_splitter, 1)

        self.tabs.addTab(page, "Circuit Reference")

    def set_context(
        self,
        mcu_name: Optional[str] = None,
        board_key: Optional[str] = None,
        theme: Optional[str] = None,
    ) -> None:
        if mcu_name:
            self._mcu_name = mcu_name
        if board_key:
            self._board_key = board_key
        if theme:
            self._theme = theme
        self.refresh_diagrams()

    def refresh_diagrams(self) -> None:
        device: McuDevice = lookup(self._mcu_name) or DEFAULT_DEVICE
        pic = get_pic_wiring(device.name)
        board = get_board_wiring(self._board_key)

        if pic.mode == MODE_ZIF_18:
            self.mode_badge.setText("ZIF-18 · JP3 = 1–2")
            self.hw_headline.setText(
                f"{board.board_name} → {device.display_name} ({pic.package} in ZIF-18 socket)"
            )
            self.hw_subline.setText(
                f"Seat {device.display_name} Pin 1 at ZIF Pin 1 (notch toward lever); set JP3 to 1–2."
            )
        elif pic.mode == MODE_ZIF_8:
            self.mode_badge.setText("ZIF-18 · JP3 = 2–3")
            self.hw_headline.setText(
                f"{board.board_name} → {device.display_name} ({pic.package} in top 8 ZIF slots)"
            )
            self.hw_subline.setText(
                f"Seat {device.display_name} in the top 8 ZIF slots; set JP3 to 2–3."
            )
        else:
            self.mode_badge.setText(f"6-wire ICSP · {pic.package}")
            self.hw_headline.setText(
                f"{board.board_name} → {device.display_name} ({pic.package} via external ICSP)"
            )
            self.hw_subline.setText(
                pic.wiring_note
                or f"Connect MCLR/VPP (Pin {pic.vpp_pin}), VDD, VSS, PGD (Pin {pic.pgd_pin}), and PGC (Pin {pic.pgc_pin}) using verified external hardware."
            )

        rows = build_wiring_rows(self._board_key, device.name)
        self.connection_count.setText(f"{len(rows)} connections")
        self.connection_count.setAccessibleDescription(
            f"{len(rows)} point-to-point connection rows for the selected profile"
        )
        self.table_note.setText(
            f"From → To for the {board.board_name} → {device.display_name} firmware profile. "
            "This table and the PIC16F84A example drawing are separate references; verify actual wiring against board documentation and the PIC datasheet."
        )
        self.wiring_table.setRowCount(len(rows))
        for row_index, (signal, source, target, note) in enumerate(rows):
            for column, value in enumerate((signal, source, target, note)):
                item = QTableWidgetItem(value)
                if column in (0, 2):
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.wiring_table.setItem(row_index, column, item)
        self.wiring_table.resizeRowsToContents()

    def _export_reference(self) -> None:
        """Export the original user-supplied PNG, not a generated wiring map."""
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Circuit Reference",
            "circuit_reference.png",
            "PNG Image (*.png)",
        )
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        Path(path).write_bytes(self.reference_view.image_bytes)
