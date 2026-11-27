"""Circuit reference image and contextual, point-to-point wiring table."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QByteArray, QPoint, QRectF, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QImage, QPainter, QWheelEvent
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.drawio import DrawioRenderError, drawio_to_svg
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


class ZoomableSvgView(QScrollArea):
    """Crisp, high-DPI SVG viewer with Ctrl+Wheel zoom and drag-to-pan."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setObjectName("svgScroll")
        self._svg_bytes = b""
        self._renderer = QSvgRenderer()
        self._zoom = 1.0
        self._fit_mode = True
        self._drag_pos: Optional[QPoint] = None
        self._canvas = _SvgCanvas(self._renderer, self)
        self.setWidget(self._canvas)
        self.setMinimumHeight(220)
        self.setMaximumHeight(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_svg(self, svg_bytes: bytes) -> None:
        self._svg_bytes = svg_bytes
        self._renderer.load(QByteArray(svg_bytes))
        self._fit_mode = True
        self._update_canvas_size()
        self._canvas.update()

    @property
    def svg_bytes(self) -> bytes:
        return self._svg_bytes

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
        self._zoom = max(0.35, min(3.5, zoom))
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
        if not self._renderer.isValid():
            return
        natural = self._renderer.defaultSize()
        if natural.width() <= 0 or natural.height() <= 0:
            return
        viewport = self.viewport().size()
        if self._fit_mode and viewport.width() > 40 and viewport.height() > 40:
            scale = min((viewport.width() - 16) / natural.width(), (viewport.height() - 16) / natural.height(), 1.35)
            self._zoom = max(scale, 0.35)
        self._canvas.setFixedSize(
            max(240, int(natural.width() * self._zoom)),
            max(180, int(natural.height() * self._zoom)),
        )
        self._canvas.update()

    def render_png(self, scale: float = 2.0) -> QImage:
        natural = self._renderer.defaultSize()
        width = max(800, int(natural.width() * scale))
        height = max(500, int(natural.height() * scale))
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.white)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._renderer.render(painter, QRectF(0, 0, width, height))
        painter.end()
        return image


class _SvgCanvas(QWidget):
    def __init__(self, renderer: QSvgRenderer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._renderer = renderer
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def paintEvent(self, _event) -> None:  # noqa: N802
        if not self._renderer.isValid():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self._renderer.render(painter, QRectF(0, 0, self.width(), self.height()))
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
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(8, 8, 8, 8)
        page_layout.setSpacing(6)

        self.reference_notice = QLabel(
            "Unverified user drawing; it may not match firmware wiring. Check the PIC datasheet and hardware guide; never connect VPP to an Arduino pin."
        )
        self.reference_notice.setObjectName("guidance")
        self.reference_notice.setAccessibleName("Circuit reference safety warning")
        self.reference_notice.setWordWrap(True)
        page_layout.addWidget(self.reference_notice)

        controls = QHBoxLayout()
        controls.setSpacing(6)
        title = QLabel("Circuit reference")
        title.setObjectName("sectionLabel")
        controls.addWidget(title, 1)
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setAccessibleName("Zoom circuit diagram out")
        self.btn_zoom_out.setToolTip("Zoom out (Ctrl+mouse wheel also works)")
        self.btn_fit = QPushButton("Fit")
        self.btn_fit.setAccessibleName("Fit circuit diagram to view")
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setAccessibleName("Zoom circuit diagram in")
        self.btn_zoom_in.setToolTip("Zoom in (Ctrl+mouse wheel also works)")
        for button in (self.btn_zoom_out, self.btn_fit, self.btn_zoom_in):
            button.setFixedSize(42, 28)
            controls.addWidget(button)
        self.btn_open_source = QPushButton("Open editable source")
        self.btn_open_source.setAccessibleName("Open editable diagrams.net circuit source")
        self.btn_open_source.setToolTip("Open the source file in the default diagrams.net-compatible editor")
        controls.addWidget(self.btn_open_source)
        page_layout.addLayout(controls)

        self.reference_view = ZoomableSvgView()
        self.reference_view.setAccessibleName("Rendered circuit connection diagram")
        self.reference_view.setAccessibleDescription(
            "Image rendered from the supplied diagrams.net XML. Use zoom controls to inspect connection labels."
        )
        source_file = _assets_reference_dir() / "user-circuit-diagram.drawio"
        self.btn_open_source.setEnabled(source_file.is_file())
        self.btn_open_source.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(source_file)))
        )
        self.btn_zoom_out.clicked.connect(self.reference_view.zoom_out)
        self.btn_fit.clicked.connect(self.reference_view.zoom_fit)
        self.btn_zoom_in.clicked.connect(self.reference_view.zoom_in)
        try:
            self.reference_view.set_svg(drawio_to_svg(source_file))
        except DrawioRenderError as exc:
            self.reference_view.setAccessibleDescription(str(exc))
            self.reference_notice.setText(
                f"The circuit source could not be displayed: {exc} Check the datasheet and hardware guide before wiring."
            )
        page_layout.addWidget(self.reference_view, 3)

        table_title = QLabel("Point-to-point connections for the selected board and PIC")
        table_title.setObjectName("sectionLabel")
        page_layout.addWidget(table_title)
        self.table_note = QLabel(
            "Firmware map only; verify pinouts against board documentation. It may not match the drawing above."
        )
        self.table_note.setObjectName("muted")
        self.table_note.setWordWrap(True)
        page_layout.addWidget(self.table_note)

        self.wiring_table = QTableWidget(0, 4)
        self.wiring_table.setObjectName("wiringTable")
        self.wiring_table.setAccessibleName("Point-to-point hardware connections")
        self.wiring_table.setAccessibleDescription(
            "Connections for the selected Arduino board and PIC target; verify them before wiring."
        )
        self.wiring_table.setHorizontalHeaderLabels(
            ["Signal", "Arduino / Shield Source", "Target PIC Pin(s)", "Hardware Notes"]
        )
        self.wiring_table.verticalHeader().setVisible(False)
        self.wiring_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.wiring_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.wiring_table.setAlternatingRowColors(True)
        self.wiring_table.setWordWrap(True)
        header = self.wiring_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.wiring_table.setMinimumHeight(140)
        self.wiring_table.setMaximumHeight(220)
        page_layout.addWidget(self.wiring_table, 2)

        content = QWidget()
        content.setLayout(page_layout)
        scroll = QScrollArea()
        scroll.setObjectName("circuitReferenceScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        self.tabs.addTab(scroll, "Circuit Reference")

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
        """Export the rendered user-supplied reference image (not a generated wiring map)."""
        default_name = "circuit_reference.svg"
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Circuit Reference",
            default_name,
            "SVG Vector (*.svg);;PNG Image (*.png)",
        )
        if not path:
            return
        if path.lower().endswith(".png") or "PNG" in selected_filter:
            if not path.lower().endswith(".png"):
                path += ".png"
            if not self.reference_view.render_png(scale=2.2).save(path):
                raise OSError(f"Could not export circuit reference image to {path}")
        else:
            if not path.lower().endswith(".svg"):
                path += ".svg"
            Path(path).write_bytes(self.reference_view.svg_bytes)
