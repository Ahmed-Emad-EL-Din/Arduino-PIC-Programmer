"""Interactive Hardware Circuit, Pinout, HEX Memory & Reference Inspector.

Provides the live right-hand engineering workbench panel (`CircuitPanel`):
  1. **Circuit Schematic** — Dynamic IEEE/IEC vector schematic (`schemdraw` SVG)
     tailored to the exact `(Arduino board, Target PIC MCU)` pair, with smooth
     zoom, pan, Reset View, and Save SVG / PNG export.
  2. **IC Pinout & ZIF Seating** — Scale-proportioned PDIP package diagram with
     Pin-1 notch, color-coded ICSP badges, ZIF-18 slot placement / JP3 jumper
     guide, and a structured pin-by-pin wiring table.
  3. **HEX Memory Map** — Visual usage bars + flat word dump (Program Flash,
     Configuration / ID words, and Data EEPROM) for the loaded `.hex` file.
  4. **Reference Build (Ho-Ro)** — Bundled `ArdPicProg_1_8_horo.png` official
     schematic and `ArdPicProg.jpg` Nano + ZIF-18 perfboard build photo, plus
     explicit compatibility warning about legacy `rweather` pinouts.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QByteArray, QPoint, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QPainter,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.circuit_drawer import generate_package_pinout_svg, generate_schematic_svg
from core.ihex import HexImage
from core.mcu_db import DEFAULT_DEVICE, McuDevice, lookup
from core.pinout_db import (
    MODE_ICSP,
    MODE_ZIF_8,
    MODE_ZIF_18,
    build_wiring_rows,
    get_board_wiring,
    get_pic_wiring,
)
from core.safety import analyze_hex_for_device


def _assets_reference_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parents[3]
    return base / "assets" / "reference"


class ZoomableSvgView(QScrollArea):
    """Crisp, high-DPI vector SVG viewer with Ctrl+Wheel / Wheel zoom & drag pan."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setObjectName("svgScroll")

        self._svg_bytes: bytes = b""
        self._renderer = QSvgRenderer()
        self._zoom: float = 1.0
        self._fit_mode: bool = True
        self._drag_pos: Optional[QPoint] = None

        self._canvas = _SvgCanvas(self._renderer, self)
        self.setWidget(self._canvas)

    def set_svg(self, svg_bytes: bytes) -> None:
        self._svg_bytes = svg_bytes
        self._renderer.load(QByteArray(svg_bytes))
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

    def _set_zoom(self, z: float) -> None:
        self._zoom = max(0.35, min(3.5, z))
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
            cur = event.position().toPoint()
            diff = cur - self._drag_pos
            self._drag_pos = cur
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_pos = None
        self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def _update_canvas_size(self) -> None:
        if not self._renderer.isValid():
            return
        nat = self._renderer.defaultSize()
        if nat.width() <= 0 or nat.height() <= 0:
            return
        vp = self.viewport().size()
        if self._fit_mode and vp.width() > 40 and vp.height() > 40:
            sx = (vp.width() - 16) / nat.width()
            sy = (vp.height() - 16) / nat.height()
            scale = min(sx, sy, 1.35)
            scale = max(scale, 0.45)
            self._zoom = scale
        target_w = max(240, int(nat.width() * self._zoom))
        target_h = max(180, int(nat.height() * self._zoom))
        self._canvas.setFixedSize(target_w, target_h)
        self._canvas.update()

    def render_png(self, scale: float = 2.0) -> QImage:
        nat = self._renderer.defaultSize()
        w = max(800, int(nat.width() * scale))
        h = max(500, int(nat.height() * scale))
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._renderer.render(p, QRectF(0, 0, w, h))
        p.end()
        return img


class _SvgCanvas(QWidget):
    def __init__(self, renderer: QSvgRenderer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._renderer = renderer
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def paintEvent(self, _event) -> None:  # noqa: N802
        if not self._renderer.isValid():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self._renderer.render(p, QRectF(0, 0, self.width(), self.height()))
        p.end()


class CircuitPanel(QWidget):
    """Live Hardware Wiring, Schematic, Pinout & HEX Memory Inspector."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("inspectorPane")

        self._mcu_name: str = "pic16f84a"
        self._board_key: str = "uno"
        self._theme: str = "dark"
        self._hex_img: Optional[HexImage] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # --- Hardware Mode Callout Banner ---
        self.banner = QFrame()
        self.banner.setObjectName("calloutCard")
        bh = QHBoxLayout(self.banner)
        bh.setContentsMargins(12, 8, 12, 8)
        bh.setSpacing(12)

        b_left = QVBoxLayout()
        b_left.setSpacing(2)
        self.hw_headline = QLabel()
        self.hw_headline.setObjectName("cardTitle")
        self.hw_subline = QLabel()
        self.hw_subline.setObjectName("muted")
        self.hw_subline.setWordWrap(True)
        b_left.addWidget(self.hw_headline)
        b_left.addWidget(self.hw_subline)
        bh.addLayout(b_left, 1)

        self.mode_badge = QLabel()
        self.mode_badge.setObjectName("modeBadge")
        self.mode_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bh.addWidget(self.mode_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(self.banner)

        # --- Main Inspector Tabs ---
        self.tabs = QTabWidget()
        self.tabs.setObjectName("inspectorTabs")
        root.addWidget(self.tabs, 1)

        # Tab 1: Dynamic Circuit Schematic
        self._build_schematic_tab()
        # Tab 2: IC Pinout & Wiring Table
        self._build_pinout_tab()
        # Tab 3: HEX Memory Map & Word Dump
        self._build_hex_tab()
        # Tab 4: Official Ho-Ro Reference Schematic & Build Photo
        self._build_reference_tab()

        self.refresh_diagrams()

    # ------------------------------------------------------------------
    # Tab Builders
    # ------------------------------------------------------------------
    def _build_schematic_tab(self) -> None:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.schem_caption = QLabel(
            "IEEE standard vector schematic — auto-configured for selected Arduino & PIC"
        )
        self.schem_caption.setObjectName("muted")
        bar.addWidget(self.schem_caption, 1)

        btn_zin = QPushButton("Zoom +")
        btn_zin.setFixedHeight(26)
        btn_zin.clicked.connect(lambda: self.schem_view.zoom_in())

        btn_zout = QPushButton("Zoom −")
        btn_zout.setFixedHeight(26)
        btn_zout.clicked.connect(lambda: self.schem_view.zoom_out())

        btn_fit = QPushButton("Fit")
        btn_fit.setFixedHeight(26)
        btn_fit.clicked.connect(lambda: self.schem_view.zoom_fit())

        btn_export = QPushButton("Export diagram…")
        btn_export.setFixedHeight(26)
        btn_export.clicked.connect(self._export_schematic)

        for b in (btn_zout, btn_fit, btn_zin, btn_export):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            bar.addWidget(b)
        lay.addLayout(bar)

        self.schem_view = ZoomableSvgView()
        lay.addWidget(self.schem_view, 1)

        self.safety_foot = QLabel()
        self.safety_foot.setObjectName("muted")
        self.safety_foot.setWordWrap(True)
        lay.addWidget(self.safety_foot)

        self.tabs.addTab(page, "Circuit Schematic")

    def _build_pinout_tab(self) -> None:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        self.pinout_view = ZoomableSvgView()
        self.pinout_view.setMinimumHeight(230)
        lay.addWidget(self.pinout_view, 3)

        tbl_lbl = QLabel("Point-to-point hardware connection table")
        tbl_lbl.setObjectName("sectionLabel")
        lay.addWidget(tbl_lbl)

        self.wiring_table = QTableWidget(0, 4)
        self.wiring_table.setObjectName("wiringTable")
        self.wiring_table.setHorizontalHeaderLabels(
            ["Signal", "Arduino / Shield Source", "Target PIC Pin(s)", "Hardware Notes"]
        )
        self.wiring_table.verticalHeader().setVisible(False)
        self.wiring_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.wiring_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.wiring_table.setAlternatingRowColors(True)
        hh = self.wiring_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.wiring_table.setMinimumHeight(155)
        lay.addWidget(self.wiring_table, 2)

        self.tabs.addTab(page, "IC Pinout && Wiring")

    def _build_hex_tab(self) -> None:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        self.hex_summary_lbl = QLabel("No HEX image loaded yet — open a .hex file or read from a PIC.")
        self.hex_summary_lbl.setWordWrap(True)
        self.hex_summary_lbl.setObjectName("muted")
        lay.addWidget(self.hex_summary_lbl)

        # Usage meters: Program Flash & Data EEPROM
        meters = QFrame()
        meters.setObjectName("subCard")
        ml = QVBoxLayout(meters)
        ml.setContentsMargins(10, 8, 10, 8)
        ml.setSpacing(6)

        r1 = QHBoxLayout()
        self.prog_meter_lbl = QLabel("Program Flash: 0 / 1024 words (0%)")
        self.prog_meter_lbl.setObjectName("monoSmall")
        r1.addWidget(self.prog_meter_lbl)
        ml.addLayout(r1)
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setFixedHeight(8)
        ml.addWidget(self.prog_bar)

        r2 = QHBoxLayout()
        self.ee_meter_lbl = QLabel("Data EEPROM: 0 / 64 bytes (0%)")
        self.ee_meter_lbl.setObjectName("monoSmall")
        r2.addWidget(self.ee_meter_lbl)
        ml.addLayout(r2)
        self.ee_bar = QProgressBar()
        self.ee_bar.setRange(0, 100)
        self.ee_bar.setValue(0)
        self.ee_bar.setTextVisible(False)
        self.ee_bar.setFixedHeight(8)
        ml.addWidget(self.ee_bar)

        self.cfg_word_lbl = QLabel("Config / ID words: —")
        self.cfg_word_lbl.setObjectName("monoSmall")
        ml.addWidget(self.cfg_word_lbl)
        lay.addWidget(meters)

        # Monospace 14-bit word inspector
        self.hex_dump = QPlainTextEdit()
        self.hex_dump.setReadOnly(True)
        self.hex_dump.setObjectName("log")
        f = QFont("DejaVu Sans Mono")
        f.setStyleHint(QFont.StyleHint.Monospace)
        f.setPointSize(9)
        self.hex_dump.setFont(f)
        self.hex_dump.setPlaceholderText(
            "Flat 14-bit word map (0x0000 Program Flash · 0x2000 Config/ID · 0x2100 EEPROM) appears here…"
        )
        lay.addWidget(self.hex_dump, 1)

        self.tabs.addTab(page, "HEX Memory Map")

    def _build_reference_tab(self) -> None:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        note = QLabel(
            "<b>Official Ho-Ro / ArdPicProg v1.8.horo hardware reference</b> — "
            "uses Arduino pins <b>D2 (VDD)</b>, <b>D3 (MCLR)</b>, <b>D4 (CLK)</b>, "
            "<b>D5 (DATA)</b>. <i>Note:</i> Legacy rweather schematics online use "
            "different pins (A1/D2/D4/D7) and inverted VPP polarity — always follow "
            "the v1.8.horo pinout shown here."
        )
        note.setWordWrap(True)
        lay.addWidget(note)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        iv = QVBoxLayout(inner)
        iv.setSpacing(14)

        ref_dir = _assets_reference_dir()
        schem_png = ref_dir / "ArdPicProg_1_8_horo.png"
        photo_jpg = ref_dir / "ArdPicProg.jpg"

        if schem_png.is_file():
            t1 = QLabel("Reference ZIF-18 shield schematic (ArdPicProg_1_8_horo.png)")
            t1.setObjectName("sectionLabel")
            iv.addWidget(t1)
            img1 = QLabel()
            img1.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img1.setStyleSheet("background:#ffffff; border-radius:6px; padding:8px;")
            pm1 = QPixmap(str(schem_png))
            if not pm1.isNull():
                img1.setPixmap(pm1.scaledToWidth(660, Qt.TransformationMode.SmoothTransformation))
            iv.addWidget(img1)

        if photo_jpg.is_file():
            t2 = QLabel("Reference Arduino Nano + 18-pin ZIF hardware build (Ho-Ro)")
            t2.setObjectName("sectionLabel")
            iv.addWidget(t2)
            img2 = QLabel()
            img2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pm2 = QPixmap(str(photo_jpg))
            if not pm2.isNull():
                img2.setPixmap(pm2.scaledToWidth(660, Qt.TransformationMode.SmoothTransformation))
            iv.addWidget(img2)

        iv.addStretch()
        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)

        self.tabs.addTab(page, "ArdPicProg Reference")

    # ------------------------------------------------------------------
    # Public State Updaters
    # ------------------------------------------------------------------
    def set_context(
        self,
        mcu_name: Optional[str] = None,
        board_key: Optional[str] = None,
        theme: Optional[str] = None,
    ) -> None:
        changed = False
        if mcu_name and mcu_name != self._mcu_name:
            self._mcu_name = mcu_name
            changed = True
        if board_key and board_key != self._board_key:
            self._board_key = board_key
            changed = True
        if theme and theme != self._theme:
            self._theme = theme
            changed = True
        if changed:
            self.refresh_diagrams()
            self._refresh_hex_inspector()

    def set_hex_image(self, img: Optional[HexImage]) -> None:
        self._hex_img = img
        self._refresh_hex_inspector()

    def refresh_diagrams(self) -> None:
        dev: McuDevice = lookup(self._mcu_name) or DEFAULT_DEVICE
        pic = get_pic_wiring(dev.name)
        ard = get_board_wiring(self._board_key)

        # Update top hardware callout banner
        if pic.mode == MODE_ZIF_18:
            self.mode_badge.setText("ZIF-18 · JP3 = 1-2")
            self.hw_headline.setText(
                f"{ard.board_name}  →  {dev.display_name} ({pic.package} in ZIF-18 Socket)"
            )
            self.hw_subline.setText(
                f"Seat {dev.display_name} Pin 1 at ZIF Pin 1 (notch up towards lever) "
                f"and set jumper JP3 to 1-2 (+5V VDD on Pin 14)."
            )
        elif pic.mode == MODE_ZIF_8:
            self.mode_badge.setText("ZIF-18 · JP3 = 2-3")
            self.hw_headline.setText(
                f"{ard.board_name}  →  {dev.display_name} ({pic.package} in ZIF-18 Top 8 Slots)"
            )
            self.hw_subline.setText(
                f"Seat {dev.display_name} in top 8 ZIF slots (Pins 1–4 in ZIF 1–4, "
                f"Pins 5–8 in ZIF 15–18) and set jumper JP3 to 2-3 (+5V VDD on Pin 1)."
            )
        else:
            self.mode_badge.setText(f"6-Wire ICSP ({pic.package})")
            self.hw_headline.setText(
                f"{ard.board_name}  →  {dev.display_name} ({pic.package} via External ICSP)"
            )
            self.hw_subline.setText(
                pic.wiring_note
                or f"Connect MCLR(Pin {pic.vpp_pin}), VDD, VSS, PGD(Pin {pic.pgd_pin}), "
                   f"and PGC(Pin {pic.pgc_pin}) on an external breadboard or target header."
            )

        # Render crisp dynamic SVG schematic + PDIP pinout
        schem_svg = generate_schematic_svg(dev.name, self._board_key, self._theme)
        pinout_svg = generate_package_pinout_svg(dev.name, self._board_key, self._theme)
        self.schem_view.set_svg(schem_svg)
        self.pinout_view.set_svg(pinout_svg)

        foot_parts = []
        if pic.safety_note:
            foot_parts.append(pic.safety_note)
        if ard.board_key == "pro_mini_8":
            foot_parts.append(ard.reset_cap_note)
        elif ard.needs_reset_cap:
            foot_parts.append(
                "Tip: Install C1 (2.2 µF between Arduino RESET and GND) AFTER flashing ProgramPic."
            )
        self.safety_foot.setText("  ·  ".join(foot_parts))

        # Populate structured wiring table
        rows = build_wiring_rows(self._board_key, dev.name)
        self.wiring_table.setRowCount(len(rows))
        for r_idx, (sig, src, dst, note) in enumerate(rows):
            for c_idx, val in enumerate((sig, src, dst, note)):
                item = QTableWidgetItem(val)
                if c_idx in (0, 2):
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                self.wiring_table.setItem(r_idx, c_idx, item)
        self.wiring_table.resizeRowsToContents()

    def _refresh_hex_inspector(self) -> None:
        dev = lookup(self._mcu_name) or DEFAULT_DEVICE
        img = self._hex_img
        if img is None or img.is_empty():
            self.hex_summary_lbl.setText(
                f"Target {dev.display_name}: {dev.program_words} Flash words, "
                f"{dev.data_bytes} EEPROM bytes — load a .hex file or click Read Backup to inspect."
            )
            self.prog_meter_lbl.setText(f"Program Flash: 0 / {dev.program_words} words (0.0%)")
            self.prog_bar.setValue(0)
            self.ee_meter_lbl.setText(f"Data EEPROM: 0 / {dev.data_bytes} bytes (0.0%)")
            self.ee_bar.setValue(0)
            self.cfg_word_lbl.setText("Config / ID words: none in buffer")
            self.hex_dump.clear()
            return

        diag = analyze_hex_for_device(img, dev)
        p_used = int(diag["prog_words"])
        e_used = int(diag["data_bytes"])
        p_pct = min(100.0, 100.0 * p_used / max(1, dev.program_words))
        e_pct = min(100.0, 100.0 * e_used / max(1, dev.data_bytes)) if dev.data_bytes else 0.0

        self.prog_meter_lbl.setText(
            f"Program Flash: {p_used} / {dev.program_words} words ({p_pct:.1f}%)"
        )
        self.prog_bar.setValue(int(round(p_pct)))

        if dev.data_bytes > 0:
            self.ee_meter_lbl.setText(
                f"Data EEPROM: {e_used} / {dev.data_bytes} bytes ({e_pct:.1f}%)"
            )
            self.ee_bar.setValue(int(round(e_pct)))
        else:
            self.ee_meter_lbl.setText("Data EEPROM: Not present on this MCU")
            self.ee_bar.setValue(0)

        flat = img.to_flat()
        cfg_addr = dev.config_start + 7
        cfg_txt = f"0x{flat[cfg_addr] & 0x3FFF:04X}" if cfg_addr in flat else "(not in HEX — erased 0x3FFF)"
        uid_vals = [
            f"{flat[dev.config_start + i] & 0x3FFF:04X}"
            for i in range(4)
            if (dev.config_start + i) in flat
        ]
        self.cfg_word_lbl.setText(
            f"Config Word @ 0x{cfg_addr:04X}: {cfg_txt}   ·   "
            f"User IDs: {', '.join(uid_vals) if uid_vals else 'none'}"
        )

        warns = list(diag.get("warnings", []))
        errs = list(diag.get("out_of_range", []))
        if errs:
            self.hex_summary_lbl.setText(
                f"⚠ Out-of-range addresses detected for {dev.display_name} "
                f"({len(errs)} word(s), first at 0x{errs[0]:04X}). Select the matching PIC MCU."
            )
        elif warns:
            self.hex_summary_lbl.setText(" · ".join(warns))
        else:
            self.hex_summary_lbl.setText(
                f"HEX image fits {dev.display_name} cleanly — ready for verified programming."
            )

        # Render formatted 8-words-per-row flat memory table (capped for instant UI)
        dump_lines = []
        prog_addrs = sorted(a for a in flat if 0 <= a < dev.program_words)
        if prog_addrs:
            dump_lines.append("=== PROGRAM FLASH (14-bit words) ===")
            row_bases = sorted({a & ~0x7 for a in prog_addrs})
            for base in row_bases[:256]:
                cells = [
                    f"{flat[base + i] & 0x3FFF:04X}" if (base + i) in flat else "...."
                    for i in range(8)
                ]
                dump_lines.append(f"  {base:04X}:  " + " ".join(cells))
            if len(row_bases) > 256:
                dump_lines.append(f"  … ({len(row_bases) - 256} additional rows omitted)")

        cfg_addrs = sorted(a for a in flat if dev.config_start <= a <= dev.config_end)
        if cfg_addrs:
            dump_lines.append("\n=== CONFIGURATION & USER ID (0x2000+) ===")
            for a in cfg_addrs:
                tag = " (Config Word)" if a == cfg_addr else (" (Device ID - skipped)" if a == dev.config_start + 6 else "")
                dump_lines.append(f"  {a:04X}:  {flat[a] & 0x3FFF:04X}{tag}")

        ee_addrs = sorted(a for a in flat if dev.data_bytes and dev.data_start <= a <= dev.data_end)
        if ee_addrs:
            dump_lines.append("\n=== DATA EEPROM (8-bit bytes @ 0x2100+) ===")
            ee_bases = sorted({a & ~0x7 for a in ee_addrs})
            for base in ee_bases:
                cells = [
                    f"{flat[base + i] & 0xFF:02X}" if (base + i) in flat else ".."
                    for i in range(8)
                ]
                dump_lines.append(f"  {base:04X} (+{base - dev.data_start:02X}):  " + " ".join(cells))

        self.hex_dump.setPlainText("\n".join(dump_lines))

    def _export_schematic(self) -> None:
        default_name = f"schematic_{self._board_key}_{self._mcu_name}.svg"
        path, flt = QFileDialog.getSaveFileName(
            self,
            "Export Circuit Schematic",
            default_name,
            "SVG Vector (*.svg);;PNG High-DPI Image (*.png)",
        )
        if not path:
            return
        if path.lower().endswith(".png") or "PNG" in flt:
            if not path.lower().endswith(".png"):
                path += ".png"
            img = self.schem_view.render_png(scale=2.2)
            img.save(path)
        else:
            if not path.lower().endswith(".svg"):
                path += ".svg"
            Path(path).write_bytes(self.schem_view.svg_bytes)
