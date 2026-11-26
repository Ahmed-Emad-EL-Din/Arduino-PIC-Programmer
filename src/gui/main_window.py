"""Main Workbench Window — Professional Two-Column Hardware Engineering UX.

Left Workbench Pane:
  1. Arduino Programmer Setup & Serial Link (Board selector, Port selector,
     Flash ProgramPic Firmware, Connect / Disconnect)
  2. Target PIC MCU & Silicon Operations (MCU selector across all 25 PICs,
     Auto-Detect Silicon, Blank Check, Read Backup, Bulk Erase)
  3. Firmware HEX Image & Verified Programming (Drag-and-drop / Open .hex,
     live usage summary, Preserve calibration checkbox, Program & Verify,
     Verify Only)

Right Live Inspector Pane (`CircuitPanel`):
  - Dynamic IEEE/IEC vector Circuit Schematic (`schemdraw` SVG) tailored to
    the exact `(Arduino Board, Target PIC MCU)` pair
  - Scale-proportioned PDIP IC Pinout, ZIF-18 seating & JP3 jumper guide, and
    point-to-point wiring table
  - HEX Memory Map & 14-bit flat word dump
  - Official `Ho-Ro/ArdPicProg` v1.8.horo reference schematic & hardware build

Bottom Dock:
  - Filterable, timestamped Activity Log + operation progress bar & Cancel.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Set, Tuple

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import (
    QAction,
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app import APP_NAME, GITHUB_URL, VERSION
from app.settings import AppSettings
from core.avrdude import BOARD_BY_KEY, BOARDS
from core.ihex import HexImage, IHexError, load_hex_file
from core.mcu_db import DEFAULT_DEVICE, McuDevice, all_devices, find_by_id, lookup
from core.pinout_db import MODE_ZIF_8, MODE_ZIF_18, get_board_wiring, get_pic_wiring
from core.programmer import ProgrammerSession
from core.safety import analyze_hex_for_device, build_summary
from core.serial_link import list_serial_ports
from .dialogs.about import AboutDialog
from .dialogs.flash_arduino import FlashArduinoDialog
from .dialogs.preflight import confirm_erase, confirm_program, show_preflight
from .dialogs.settings_dialog import SettingsDialog
from .icons import icon
from .theme import build_qss, tokens_for
from .widgets.circuit_panel import CircuitPanel
from .widgets.log_pane import LogPane
from .workers import SingleLane, Worker

ARDPICPROG_URL = "https://github.com/Ho-Ro/ArdPicProg"
QPICKIT_URL = "https://github.com/Ho-Ro/QPICkit"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = AppSettings()
        self.session = ProgrammerSession(use_binary=True)
        self.lane = SingleLane()
        self.hex_img: Optional[HexImage] = None
        self.hex_path: str = ""
        self.target: McuDevice = lookup(self.settings.mcu) or DEFAULT_DEVICE
        self.board_key: str = (
            self.settings.board_key if self.settings.board_key in BOARD_BY_KEY else "uno"
        )
        # Track acknowledged preflight per `(board_key, mcu_name)` pair so
        # changing MCU or Arduino board re-verifies the new wiring!
        self._preflight_verified_pairs: Set[Tuple[str, str]] = set()

        self.setWindowTitle(f"{APP_NAME}  ·  v{VERSION}")
        self.setMinimumSize(1160, 740)
        self.resize(1340, 840)
        self.setAcceptDrops(True)

        self._build_ui()
        self._build_menus_and_toolbar()
        self.apply_theme(self.settings.theme, self.settings.font_size)

        geo = self.settings.geometry
        if geo is not None:
            self.restoreGeometry(geo)
        st = self.settings.window_state
        if st is not None:
            self.restoreState(st)

        self._refresh_ports()
        self._sync_inspector()
        self._refresh_hex_summary()
        self._refresh_actions()

        self.log(
            f"{APP_NAME} v{VERSION} ready — select your Arduino board & PIC MCU to inspect "
            "the exact circuit schematic, connect the programmer, and upload a .hex image.",
            "OK",
        )

    # ------------------------------------------------------------------
    # Workbench Layout Construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("page")
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- 1. Top Hardware Status Strip ----
        header = QFrame()
        header.setObjectName("headerBar")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 10, 16, 10)
        hl.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        t_lbl = QLabel(APP_NAME)
        t_lbl.setObjectName("appTitle")
        sub_lbl = QLabel(
            "Arduino-based PIC16F / PIC12F HV ICSP & ZIF-18 workbench (ProgramPic v1.8.horo)"
        )
        sub_lbl.setObjectName("muted")
        title_col.addWidget(t_lbl)
        title_col.addWidget(sub_lbl)
        hl.addLayout(title_col)
        hl.addStretch()

        self.chip_board = QLabel()
        self.chip_prog = QLabel()
        self.chip_target = QLabel()
        self.chip_file = QLabel()
        for ch in (self.chip_board, self.chip_prog, self.chip_target, self.chip_file):
            ch.setObjectName("chip")
            hl.addWidget(ch)
        outer.addWidget(header)

        # ---- 2. Main Two-Column Splitter ----
        self.main_split = QSplitter(Qt.Orientation.Horizontal)
        self.main_split.setChildrenCollapsible(False)

        # Left Pane: Scrollable Guided Control Workbench
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setMinimumWidth(490)
        left_scroll.setMaximumWidth(610)

        left_body = QWidget()
        left_body.setObjectName("leftWorkbench")
        left_body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lcol = QVBoxLayout(left_body)
        lcol.setContentsMargins(14, 12, 12, 12)
        lcol.setSpacing(10)

        lcol.addWidget(self._build_programmer_card())
        lcol.addWidget(self._build_target_card())
        lcol.addWidget(self._build_firmware_card())
        lcol.addStretch(1)
        left_scroll.setWidget(left_body)

        # Right Pane: Live Circuit Schematic, IC Pinout & HEX Memory Inspector
        right_wrap = QWidget()
        right_wrap.setObjectName("inspectorPane")
        right_wrap.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        rcol = QVBoxLayout(right_wrap)
        rcol.setContentsMargins(8, 12, 14, 12)
        rcol.setSpacing(0)
        self.circuit_panel = CircuitPanel(self)
        rcol.addWidget(self.circuit_panel, 1)

        self.main_split.addWidget(left_scroll)
        self.main_split.addWidget(right_wrap)
        self.main_split.setStretchFactor(0, 0)
        self.main_split.setStretchFactor(1, 1)
        self.main_split.setSizes([510, 830])
        outer.addWidget(self.main_split, 1)

        # ---- 3. Bottom Progress & Action Status Bar ----
        prog_strip = QFrame()
        prog_strip.setObjectName("headerBar")
        psl = QHBoxLayout(prog_strip)
        psl.setContentsMargins(16, 6, 16, 6)
        psl.setSpacing(10)

        self.status_lbl = QLabel("Idle — hardware state not measured")
        self.status_lbl.setObjectName("muted")
        psl.addWidget(self.status_lbl, 2)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setMaximumWidth(280)
        psl.addWidget(self.progress, 1)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("dangerOutline")
        self.btn_cancel.setFixedHeight(26)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_current)
        psl.addWidget(self.btn_cancel)
        outer.addWidget(prog_strip)

        self.setCentralWidget(central)

        # ---- 4. Bottom Activity Log Dock ----
        self.log_pane = LogPane(self)
        self.log_dock = QDockWidget("Activity Log", self)
        self.log_dock.setObjectName("activityLogDock")
        self.log_dock.setWidget(self.log_pane)
        self.log_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea
        )
        self.log_dock.setMinimumHeight(130)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        self.log_dock.setVisible(self.settings.log_visible)
        self.log_dock.visibilityChanged.connect(self._on_dock_visibility)

    def _make_card_header(self, num: str, title: str, subtitle: str) -> QVBoxLayout:
        v = QVBoxLayout()
        v.setSpacing(2)
        top = QHBoxLayout()
        top.setSpacing(8)
        badge = QLabel(num)
        badge.setObjectName("stepNum")
        badge.setFixedSize(22, 22)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_lbl = QLabel(title)
        t_lbl.setObjectName("cardTitle")
        top.addWidget(badge)
        top.addWidget(t_lbl, 1)
        v.addLayout(top)
        s_lbl = QLabel(subtitle)
        s_lbl.setObjectName("muted")
        s_lbl.setWordWrap(True)
        v.addWidget(s_lbl)
        return v

    def _build_programmer_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        lay.addLayout(
            self._make_card_header(
                "1",
                "Arduino Programmer Link",
                "Select your host Arduino board, flash ProgramPic once, then connect.",
            )
        )

        form = QFormLayout()
        form.setContentsMargins(0, 4, 0, 0)
        form.setSpacing(8)

        self.cmb_board = QComboBox()
        self.cmb_board.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cmb_board.setMinimumContentsLength(18)
        for b in BOARDS:
            self.cmb_board.addItem(b.label, b.key)
        b_idx = self.cmb_board.findData(self.board_key)
        self.cmb_board.setCurrentIndex(max(0, b_idx))
        self.cmb_board.currentIndexChanged.connect(self._on_board_changed)
        form.addRow("Arduino board:", self.cmb_board)

        port_row = QHBoxLayout()
        port_row.setContentsMargins(0, 0, 0, 0)
        port_row.setSpacing(6)
        self.cmb_port = QComboBox()
        self.cmb_port.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cmb_port.setMinimumContentsLength(14)
        self.btn_rescan = QPushButton("Rescan")
        self.btn_rescan.clicked.connect(self._refresh_ports)
        port_row.addWidget(self.cmb_port, 1)
        port_row.addWidget(self.btn_rescan)
        port_wrap = QWidget()
        port_wrap.setLayout(port_row)
        form.addRow("Serial port:", port_wrap)
        lay.addLayout(form)

        self.lbl_board_note = QLabel()
        self.lbl_board_note.setObjectName("muted")
        self.lbl_board_note.setWordWrap(True)
        lay.addWidget(self.lbl_board_note)

        btns = QHBoxLayout()
        btns.setSpacing(6)
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("primary")
        self.btn_connect.clicked.connect(self._connect)

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.clicked.connect(self._disconnect)

        self.btn_flash_ard = QPushButton("Flash Arduino…")
        self.btn_flash_ard.setToolTip(
            "Upload ProgramPic v1.8.horo firmware onto the selected Arduino via avrdude"
        )
        self.btn_flash_ard.clicked.connect(self._flash_arduino)

        btns.addWidget(self.btn_connect, 2)
        btns.addWidget(self.btn_disconnect, 2)
        btns.addWidget(self.btn_flash_ard, 2)
        lay.addLayout(btns)
        return card

    def _build_target_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        lay.addLayout(
            self._make_card_header(
                "2",
                "Target PIC Microcontroller",
                "Pick the exact PIC MCU — updates the schematic, PDIP pinout & safety gates.",
            )
        )

        mcu_row = QHBoxLayout()
        mcu_row.setSpacing(6)
        self.cmb_mcu = QComboBox()
        self.cmb_mcu.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cmb_mcu.setMinimumContentsLength(18)
        for dev in all_devices():
            pw = get_pic_wiring(dev.name)
            id_tag = "Auto-ID" if dev.has_device_id else "Manual"
            mode_tag = f"JP3={pw.jp3_position}" if pw.uses_zif else "ICSP"
            self.cmb_mcu.addItem(
                f"{dev.display_name}  ·  {pw.package} ({mode_tag}, {id_tag})",
                dev.name,
            )
        m_idx = self.cmb_mcu.findData(self.target.name)
        self.cmb_mcu.setCurrentIndex(max(0, m_idx))
        self.cmb_mcu.currentIndexChanged.connect(self._on_mcu_changed)
        mcu_row.addWidget(self.cmb_mcu, 1)

        self.btn_detect = QPushButton("Query Programmer")
        self.btn_detect.setToolTip(
            "Ask ProgramPic to report the target model. Raw silicon ID and socket voltage "
            "are not exposed to this app."
        )
        self.btn_detect.clicked.connect(self._detect)
        mcu_row.addWidget(self.btn_detect)
        lay.addLayout(mcu_row)

        # Silicon specs mini-card
        spec_box = QFrame()
        spec_box.setObjectName("subCard")
        sbl = QVBoxLayout(spec_box)
        sbl.setContentsMargins(10, 6, 10, 6)
        sbl.setSpacing(2)
        self.lbl_mcu_specs = QLabel()
        self.lbl_mcu_specs.setObjectName("monoSmall")
        self.lbl_mcu_specs.setWordWrap(True)
        self.lbl_silicon_probe = QLabel("Programmer report: not queried yet")
        self.lbl_silicon_probe.setObjectName("muted")
        sbl.addWidget(self.lbl_mcu_specs)
        sbl.addWidget(self.lbl_silicon_probe)
        lay.addWidget(spec_box)

        # Non-HEX Silicon Utilities: Blank Check, Read Backup, Bulk Erase
        grid = QGridLayout()
        grid.setSpacing(6)
        self.btn_blank = QPushButton("Blank Check")
        self.btn_blank.clicked.connect(self._blank_check)

        self.btn_read = QPushButton("Read Backup…")
        self.btn_read.clicked.connect(self._read_chip)

        self.btn_erase = QPushButton("Erase Chip…")
        self.btn_erase.setObjectName("dangerOutline")
        self.btn_erase.clicked.connect(self._erase)

        grid.addWidget(self.btn_blank, 0, 0)
        grid.addWidget(self.btn_read, 0, 1)
        grid.addWidget(self.btn_erase, 0, 2)
        lay.addLayout(grid)
        return card

    def _build_firmware_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        lay.addLayout(
            self._make_card_header(
                "3",
                "Firmware Image (.hex) & Write",
                "Open or drop an Intel HEX file. Memory bounds & silicon ID are checked before write.",
            )
        )

        file_row = QHBoxLayout()
        file_row.setSpacing(6)
        self.btn_open_hex = QPushButton("Open HEX File…")
        self.btn_open_hex.clicked.connect(self.open_hex)

        self.btn_reload_hex = QPushButton("Reload")
        self.btn_reload_hex.setToolTip("Reload the current .hex file from disk")
        self.btn_reload_hex.clicked.connect(self._reload_hex)

        self.btn_inspect_hex = QPushButton("Inspect Map")
        self.btn_inspect_hex.setToolTip("Open the HEX Memory Map tab on the right")
        self.btn_inspect_hex.clicked.connect(lambda: self.circuit_panel.tabs.setCurrentIndex(2))

        file_row.addWidget(self.btn_open_hex, 2)
        file_row.addWidget(self.btn_reload_hex, 1)
        file_row.addWidget(self.btn_inspect_hex, 1)
        lay.addLayout(file_row)

        hex_box = QFrame()
        hex_box.setObjectName("subCard")
        hbl = QVBoxLayout(hex_box)
        hbl.setContentsMargins(10, 8, 10, 8)
        hbl.setSpacing(3)
        self.lbl_hex_name = QLabel("No .hex file loaded (drag & drop a .hex file anywhere)")
        self.lbl_hex_name.setWordWrap(True)
        self.lbl_hex_stats = QLabel("Program: —  ·  EEPROM: —  ·  Config: —")
        self.lbl_hex_stats.setObjectName("monoSmall")
        self.lbl_hex_stats.setWordWrap(True)
        hbl.addWidget(self.lbl_hex_name)
        hbl.addWidget(self.lbl_hex_stats)
        lay.addWidget(hex_box)

        self.chk_preserve_cal = QCheckBox(
            "Preserve factory OSCCAL & bandgap calibration bits (recommended)"
        )
        self.chk_preserve_cal.setChecked(True)
        lay.addWidget(self.chk_preserve_cal)

        act_row = QHBoxLayout()
        act_row.setSpacing(6)
        self.btn_program = QPushButton("Program && Verify PIC")
        self.btn_program.setObjectName("primary")
        self.btn_program.setMinimumHeight(36)
        self.btn_program.clicked.connect(self._program)

        self.btn_verify = QPushButton("Verify Only")
        self.btn_verify.setMinimumHeight(36)
        self.btn_verify.clicked.connect(self._verify_only)

        act_row.addWidget(self.btn_program, 2)
        act_row.addWidget(self.btn_verify, 1)
        lay.addLayout(act_row)
        return card

    # ------------------------------------------------------------------
    # Menus & Primary Toolbar
    # ------------------------------------------------------------------
    def _build_menus_and_toolbar(self) -> None:
        mb = self.menuBar()

        # FILE
        m_file = mb.addMenu("&File")
        self.act_open = QAction("Open HEX…", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self.open_hex)
        m_file.addAction(self.act_open)

        self.menu_recent = QMenu("Open &Recent", self)
        m_file.addMenu(self.menu_recent)
        self._rebuild_recent()

        self.act_save = QAction("Read Chip && Save HEX…", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self._read_chip)
        m_file.addAction(self.act_save)

        self.act_export_schem = QAction("Export Circuit Schematic…", self)
        self.act_export_schem.triggered.connect(self.circuit_panel._export_schematic)
        m_file.addAction(self.act_export_schem)

        self.act_export_log = QAction("Export Activity Log…", self)
        self.act_export_log.triggered.connect(self.log_pane._save)
        m_file.addAction(self.act_export_log)

        m_file.addSeparator()
        act_exit = QAction("E&xit", self)
        act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        act_exit.triggered.connect(self.close)
        m_file.addAction(act_exit)

        # PROGRAMMER
        m_prog = mb.addMenu("&Programmer")
        self.act_ports = QAction("Rescan Serial Ports", self)
        self.act_ports.setShortcut(QKeySequence("F5"))
        self.act_ports.triggered.connect(self._refresh_ports)
        m_prog.addAction(self.act_ports)

        self.act_flash = QAction("Flash Arduino Firmware…", self)
        self.act_flash.triggered.connect(self._flash_arduino)
        m_prog.addAction(self.act_flash)

        m_prog.addSeparator()
        self.act_connect = QAction("&Connect Programmer", self)
        self.act_connect.setShortcut(QKeySequence("Ctrl+P"))
        self.act_connect.triggered.connect(self._connect)
        m_prog.addAction(self.act_connect)

        self.act_disconnect = QAction("Disconnect", self)
        self.act_disconnect.triggered.connect(self._disconnect)
        m_prog.addAction(self.act_disconnect)

        m_prog.addSeparator()
        self.act_detect = QAction("Auto-Detect PIC", self)
        self.act_detect.setShortcut(QKeySequence("F6"))
        self.act_detect.triggered.connect(self._detect)
        m_prog.addAction(self.act_detect)

        self.act_blank = QAction("Blank Check", self)
        self.act_blank.triggered.connect(self._blank_check)
        m_prog.addAction(self.act_blank)

        self.act_program = QAction("Program && Verify PIC…", self)
        self.act_program.setShortcut(QKeySequence("Ctrl+R"))
        self.act_program.triggered.connect(self._program)
        m_prog.addAction(self.act_program)

        self.act_verify = QAction("Verify Chip vs HEX", self)
        self.act_verify.triggered.connect(self._verify_only)
        m_prog.addAction(self.act_verify)

        self.act_erase = QAction("Bulk Erase Chip…", self)
        self.act_erase.triggered.connect(self._erase)
        m_prog.addAction(self.act_erase)

        m_prog.addSeparator()
        self.act_info = QAction("Session & Hardware Summary", self)
        self.act_info.triggered.connect(self._show_info)
        m_prog.addAction(self.act_info)

        # VIEW
        m_view = mb.addMenu("&View")
        self.act_log = QAction("Show Activity &Log", self)
        self.act_log.setCheckable(True)
        self.act_log.setChecked(self.settings.log_visible)
        self.act_log.setShortcut(QKeySequence("Ctrl+L"))
        self.act_log.toggled.connect(self._toggle_log)
        m_view.addAction(self.act_log)

        m_view.addSeparator()
        act_t_schem = QAction("Show Circuit Schematic Tab", self)
        act_t_schem.setShortcut(QKeySequence("Alt+1"))
        act_t_schem.triggered.connect(lambda: self.circuit_panel.tabs.setCurrentIndex(0))
        m_view.addAction(act_t_schem)

        act_t_pin = QAction("Show IC Pinout && Wiring Tab", self)
        act_t_pin.setShortcut(QKeySequence("Alt+2"))
        act_t_pin.triggered.connect(lambda: self.circuit_panel.tabs.setCurrentIndex(1))
        m_view.addAction(act_t_pin)

        act_t_hex = QAction("Show HEX Memory Map Tab", self)
        act_t_hex.setShortcut(QKeySequence("Alt+3"))
        act_t_hex.triggered.connect(lambda: self.circuit_panel.tabs.setCurrentIndex(2))
        m_view.addAction(act_t_hex)

        act_t_ref = QAction("Show ArdPicProg Reference Tab", self)
        act_t_ref.setShortcut(QKeySequence("Alt+4"))
        act_t_ref.triggered.connect(lambda: self.circuit_panel.tabs.setCurrentIndex(3))
        m_view.addAction(act_t_ref)

        m_view.addSeparator()
        act_zin = QAction("Increase UI Font Size", self)
        act_zin.setShortcut(QKeySequence.StandardKey.ZoomIn)
        act_zin.triggered.connect(lambda: self._zoom_font(+1))
        m_view.addAction(act_zin)

        act_zout = QAction("Decrease UI Font Size", self)
        act_zout.setShortcut(QKeySequence.StandardKey.ZoomOut)
        act_zout.triggered.connect(lambda: self._zoom_font(-1))
        m_view.addAction(act_zout)

        act_zrst = QAction("Reset UI Font Size", self)
        act_zrst.triggered.connect(lambda: self._zoom_font(0))
        m_view.addAction(act_zrst)

        m_view.addSeparator()
        self.act_theme = QAction("Switch Dark / Light Theme", self)
        self.act_theme.setShortcut(QKeySequence("Ctrl+T"))
        self.act_theme.triggered.connect(self._toggle_theme)
        m_view.addAction(self.act_theme)

        # SETTINGS
        m_set = mb.addMenu("&Settings")
        self.act_settings = QAction("Preferences && Safety…", self)
        self.act_settings.setShortcut(QKeySequence("Ctrl+,"))
        self.act_settings.triggered.connect(self._open_settings)
        m_set.addAction(self.act_settings)

        # HELP
        m_help = mb.addMenu("&Help")
        self.act_guide = QAction("User Guide && Troubleshooting", self)
        self.act_guide.setShortcut(QKeySequence.StandardKey.HelpContents)
        self.act_guide.triggered.connect(self._user_guide)
        m_help.addAction(self.act_guide)

        act_horo = QAction("Ho-Ro/ArdPicProg Repository (GitHub)", self)
        act_horo.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(ARDPICPROG_URL)))
        m_help.addAction(act_horo)

        act_author = QAction("Author GitHub Profile", self)
        act_author.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL)))
        m_help.addAction(act_author)

        m_help.addSeparator()
        self.act_about = QAction(f"About {APP_NAME}…", self)
        self.act_about.triggered.connect(lambda: AboutDialog(self).exec())
        m_help.addAction(self.act_about)

        # ---- Top Action Toolbar ----
        tb = QToolBar("Workbench Toolbar", self)
        tb.setObjectName("mainToolbar")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        tb.addAction(self.act_open)
        tb.addSeparator()
        tb.addAction(self.act_flash)
        tb.addAction(self.act_connect)
        tb.addAction(self.act_detect)
        tb.addSeparator()
        tb.addAction(self.act_program)
        tb.addAction(self.act_verify)
        tb.addAction(self.act_save)
        tb.addSeparator()
        tb.addAction(self.act_theme)
        tb.addAction(self.act_settings)
        tb.addAction(self.act_guide)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

    # ------------------------------------------------------------------
    # Theme & Icon Synchronization
    # ------------------------------------------------------------------
    def apply_theme(self, theme: str, font_size: int = 10) -> None:
        t = tokens_for(theme)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_qss(t, font_size))

        ic_col = t.subtext
        self.act_open.setIcon(icon("open", ic_col))
        self.act_save.setIcon(icon("download", ic_col))
        self.act_export_schem.setIcon(icon("circuit", ic_col))
        self.act_export_log.setIcon(icon("log", ic_col))
        self.act_ports.setIcon(icon("refresh", ic_col))
        self.act_flash.setIcon(icon("upload", ic_col))
        self.act_connect.setIcon(icon("plug", t.success if self.session.connected else ic_col))
        self.act_disconnect.setIcon(icon("unplug", ic_col))
        self.act_detect.setIcon(icon("chip", ic_col))
        self.act_blank.setIcon(icon("check", ic_col))
        self.act_program.setIcon(icon("play", t.accent))
        self.act_verify.setIcon(icon("shield", ic_col))
        self.act_erase.setIcon(icon("erase", t.danger))
        self.act_theme.setIcon(icon("theme", ic_col))
        self.act_settings.setIcon(icon("settings", ic_col))
        self.act_guide.setIcon(icon("help", ic_col))
        self.act_info.setIcon(icon("info", ic_col))

        self.log_pane.set_theme(t.name)
        self.circuit_panel.set_context(
            mcu_name=self.target.name,
            board_key=self.board_key,
            theme=t.name,
        )

    def _toggle_theme(self) -> None:
        new_theme = "light" if self.settings.theme == "dark" else "dark"
        self.settings.theme = new_theme
        self.apply_theme(new_theme, self.settings.font_size)
        self.log(f"Switched appearance to {new_theme} theme.", "INFO")

    def _zoom_font(self, step: int) -> None:
        if step == 0:
            fs = 10
        else:
            fs = max(9, min(14, self.settings.font_size + step))
        self.settings.font_size = fs
        self.apply_theme(self.settings.theme, fs)

    def _toggle_log(self, visible: bool) -> None:
        self.log_dock.setVisible(visible)
        self.settings.log_visible = visible

    def _on_dock_visibility(self, visible: bool) -> None:
        self.act_log.blockSignals(True)
        self.act_log.setChecked(visible)
        self.act_log.blockSignals(False)

    # ------------------------------------------------------------------
    # State Synchronization & Selectors
    # ------------------------------------------------------------------
    def _set_chip_state(self, lbl: QLabel, text: str, variant: str = "neutral") -> None:
        obj = {
            "ok": "chipOk",
            "warn": "chipWarn",
            "bad": "chipBad",
        }.get(variant, "chip")
        lbl.setText(text)
        if lbl.objectName() != obj:
            lbl.setObjectName(obj)
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)

    def _on_board_changed(self) -> None:
        bkey = str(self.cmb_board.currentData() or "uno")
        self.board_key = bkey
        self.settings.board_key = bkey
        self._sync_inspector()
        self._refresh_actions()

    def _on_mcu_changed(self) -> None:
        mname = str(self.cmb_mcu.currentData() or "pic16f84a")
        dev = lookup(mname) or DEFAULT_DEVICE
        self.target = dev
        self.settings.mcu = dev.name
        # Preserve calibration checkbox only applies to MCUs with calibration words/bits
        has_cal = dev.reserved_words > 0 or dev.config_save_mask != 0
        self.chk_preserve_cal.setEnabled(has_cal)
        self._sync_inspector()
        self._refresh_hex_summary()
        self._refresh_actions()

    def _sync_inspector(self) -> None:
        bw = get_board_wiring(self.board_key)
        pw = get_pic_wiring(self.target.name)

        if self.board_key == "pro_mini_5v":
            self.lbl_board_note.setText(
                "⚠ Use only the 5V / 16MHz Pro Mini. A 3.3V variant is not electrically compatible."
            )
            self.lbl_board_note.setObjectName("warn")
        elif bw.needs_reset_cap:
            self.lbl_board_note.setText(
                f"Pins: {bw.vdd_pin}=VDD, {bw.mclr_pin}=MCLR, {bw.clk_pin}=CLK, "
                f"{bw.data_pin}=DATA · Add 2.2 µF {bw.reset_pin}-GND cap after flashing."
            )
            self.lbl_board_note.setObjectName("muted")
        else:
            self.lbl_board_note.setText(
                f"Pins: {bw.vdd_pin}=VDD, {bw.mclr_pin}=MCLR, {bw.clk_pin}=CLK, "
                f"{bw.data_pin}=DATA · Native USB CDC (no 2.2 µF cap needed)."
            )
            self.lbl_board_note.setObjectName("muted")
        self.lbl_board_note.style().unpolish(self.lbl_board_note)
        self.lbl_board_note.style().polish(self.lbl_board_note)

        cal_str = "OSCCAL preserved" if (self.target.reserved_words or self.target.config_save_mask) else "No OSCCAL"
        self.lbl_mcu_specs.setText(
            f"Flash: {self.target.program_words} w  ·  EEPROM: {self.target.data_bytes} B  ·  "
            f"{pw.package}  ·  {cal_str}"
        )

        self.circuit_panel.set_context(
            mcu_name=self.target.name,
            board_key=self.board_key,
            theme=self.settings.theme,
        )

    def _refresh_ports(self) -> None:
        prev = str(self.cmb_port.currentData() or self.settings.port or "")
        self.cmb_port.clear()
        ports = list_serial_ports()
        for p in ports:
            prefix = "★ " if p.is_likely_arduino else ""
            self.cmb_port.addItem(f"{prefix}{p.label()}", p.device)
        if not ports:
            self.cmb_port.addItem("No serial ports detected", "")
        else:
            for i in range(self.cmb_port.count()):
                if self.cmb_port.itemData(i) == prev:
                    self.cmb_port.setCurrentIndex(i)
                    break

    def _refresh_hex_summary(self) -> None:
        self.circuit_panel.set_hex_image(self.hex_img)
        if self.hex_img is None or self.hex_img.is_empty():
            self.lbl_hex_name.setText("No .hex file loaded (drag & drop a .hex file anywhere)")
            self.lbl_hex_stats.setText("Program: —  ·  EEPROM: —  ·  Config: —")
            self._set_chip_state(self.chip_file, "HEX: none", "neutral")
            return

        fname = Path(self.hex_path).name if self.hex_path else "memory_read.hex"
        diag = analyze_hex_for_device(self.hex_img, self.target)
        pw = int(diag["prog_words"])
        eb = int(diag["data_bytes"])
        cw = int(diag["cfg_words"])
        oot = list(diag["out_of_range"])

        self.lbl_hex_name.setText(f"Loaded: {fname}")
        self.lbl_hex_stats.setText(
            f"Program: {pw}/{self.target.program_words} w  ·  "
            f"EEPROM: {eb}/{self.target.data_bytes} B  ·  Config: {cw} w"
        )
        if oot:
            self._set_chip_state(self.chip_file, f"HEX: {fname} (Range Mismatch)", "bad")
        else:
            self._set_chip_state(self.chip_file, f"HEX: {fname}", "ok")

    def _refresh_actions(self) -> None:
        busy = self.lane.busy
        conn = self.session.connected
        has_hex = self.hex_img is not None and not self.hex_img.is_empty()

        bw = get_board_wiring(self.board_key)
        self._set_chip_state(
            self.chip_board,
            f"Board: {bw.board_name}",
            "warn" if self.board_key == "pro_mini_5v" else "neutral",
        )
        if conn:
            self._set_chip_state(
                self.chip_prog,
                f"Programmer: {self.session.state.port} (v{self.session.state.firmware})",
                "ok",
            )
        else:
            self._set_chip_state(self.chip_prog, "Programmer: Disconnected", "neutral")

        pw = get_pic_wiring(self.target.name)
        mode_lbl = f"JP3={pw.jp3_position}" if pw.uses_zif else "ICSP"
        self._set_chip_state(
            self.chip_target,
            f"Target selected: {self.target.display_name} ({mode_lbl})",
            "neutral",
        )

        # Control states
        self.cmb_board.setEnabled(not busy)
        self.cmb_port.setEnabled(not busy and not conn)
        self.btn_rescan.setEnabled(not busy and not conn)
        self.btn_flash_ard.setEnabled(not busy and not conn)
        self.btn_connect.setEnabled(not busy and not conn)
        self.btn_disconnect.setEnabled(not busy and conn)

        self.cmb_mcu.setEnabled(not busy)
        self.btn_detect.setEnabled(not busy and conn)
        self.btn_blank.setEnabled(not busy and conn)
        self.btn_read.setEnabled(not busy and conn)
        self.btn_erase.setEnabled(not busy and conn)

        self.btn_open_hex.setEnabled(not busy)
        self.btn_reload_hex.setEnabled(not busy and bool(self.hex_path))
        self.btn_program.setEnabled(not busy and conn and has_hex)
        self.btn_verify.setEnabled(not busy and conn and has_hex)
        self.btn_cancel.setEnabled(busy)

        # Menu actions
        self.act_flash.setEnabled(not busy and not conn)
        self.act_connect.setEnabled(not busy and not conn)
        self.act_disconnect.setEnabled(not busy and conn)
        self.act_detect.setEnabled(not busy and conn)
        self.act_blank.setEnabled(not busy and conn)
        self.act_save.setEnabled(not busy and conn)
        self.act_erase.setEnabled(not busy and conn)
        self.act_program.setEnabled(not busy and conn and has_hex)
        self.act_verify.setEnabled(not busy and conn and has_hex)

    # ------------------------------------------------------------------
    # Logging & Background Task Runner
    # ------------------------------------------------------------------
    def log(self, msg: str, level: str = "INFO") -> None:
        self.log_pane.log(msg, level)

    def _set_pct(self, done: int, total: int) -> None:
        if total > 0:
            val = max(0, min(100, int(100 * done / total)))
            self.progress.setValue(val)

    def _cancel_current(self) -> None:
        if self.lane.busy:
            self.session.request_cancel()
            self.lane.cancel()
            self.log("Cancellation requested. The current serial command will finish before the host closes the port safely.", "WARN")
            self.status_lbl.setText("Waiting for the current hardware command to finish safely…")

    def _ensure_preflight(self) -> bool:
        pair = (self.board_key, self.target.name)
        seen = pair in self._preflight_verified_pairs
        if show_preflight(self, seen, dev=self.target, board_key=self.board_key):
            self._preflight_verified_pairs.add(pair)
            return True
        self.log("Operation aborted at hardware preflight checklist.", "WARN")
        return False

    def _run_task(self, fn, on_ok, label: str) -> None:
        if self.lane.busy:
            QMessageBox.information(self, "Busy", "Wait for the active hardware operation to finish.")
            return
        self.progress.setValue(0)
        self.status_lbl.setText(f"Running: {label}…")
        worker = Worker(fn, name=label, parent=self)
        worker.progressed.connect(lambda line: self.log(line, "INFO"))
        worker.percented.connect(self._set_pct)

        def _done_ok(res) -> None:
            self._refresh_actions()
            on_ok(res)

        def _done_err(err_msg: str) -> None:
            self.progress.setValue(0)
            self._refresh_actions()
            self.log(err_msg, "ERR")
            self.status_lbl.setText(f"Stopped: {err_msg.splitlines()[0]}")
            QMessageBox.warning(self, f"{label} stopped", err_msg)

        worker.succeeded.connect(_done_ok)
        worker.failed.connect(_done_err)
        self.lane.start(worker)
        self._refresh_actions()

    # ------------------------------------------------------------------
    # HEX File Loading & Drag-and-Drop
    # ------------------------------------------------------------------
    def open_hex(self, path: Optional[str] = None) -> None:
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Open Intel HEX Firmware",
                str(Path(self.hex_path).parent) if self.hex_path else "",
                "Intel HEX (*.hex *.ihx);;All files (*)",
            )
        if not path:
            return
        self._load_hex_from_path(path)

    def _reload_hex(self) -> None:
        if self.hex_path:
            self._load_hex_from_path(self.hex_path)

    def _load_hex_from_path(self, path: str) -> None:
        try:
            img = load_hex_file(path)
            if img.is_empty():
                raise IHexError("The selected HEX file contains zero data bytes.")
        except (OSError, IHexError) as exc:
            self.log(f"Failed to load HEX '{path}': {exc}", "ERR")
            QMessageBox.critical(self, "Invalid Intel HEX file", str(exc))
            return

        self.hex_img = img
        self.hex_path = str(path)
        self.settings.add_recent(self.hex_path)
        self._rebuild_recent()
        self._refresh_hex_summary()
        self._refresh_actions()

        diag = analyze_hex_for_device(img, self.target)
        self.log(
            f"Loaded {Path(path).name} ({len(img.data)} bytes: "
            f"{diag['prog_words']} Flash words, {diag['data_bytes']} EEPROM bytes, "
            f"{diag['cfg_words']} Config/ID words).",
            "OK",
        )
        for w in diag["warnings"]:
            self.log(w, "WARN")
        if diag["out_of_range"]:
            self.log(
                f"HEX contains {len(diag['out_of_range'])} word(s) outside "
                f"{self.target.display_name} memory map — check your Target PIC selection.",
                "WARN",
            )

    def _rebuild_recent(self) -> None:
        self.menu_recent.clear()
        recents = [p for p in self.settings.recent_files if Path(p).is_file()]
        if not recents:
            empty = QAction("(No recent files)", self)
            empty.setEnabled(False)
            self.menu_recent.addAction(empty)
            return
        for p in recents:
            act = QAction(p, self)
            act.triggered.connect(lambda _chk=False, fp=p: self._load_hex_from_path(fp))
            self.menu_recent.addAction(act)

    def dragEnterEvent(self, ev: QDragEnterEvent) -> None:  # noqa: N802
        if ev.mimeData().hasUrls():
            for u in ev.mimeData().urls():
                if u.isLocalFile() and u.toLocalFile().lower().endswith((".hex", ".ihx")):
                    ev.acceptProposedAction()
                    return
        ev.ignore()

    def dropEvent(self, ev: QDropEvent) -> None:  # noqa: N802
        for u in ev.mimeData().urls():
            if u.isLocalFile() and u.toLocalFile().lower().endswith((".hex", ".ihx")):
                self._load_hex_from_path(u.toLocalFile())
                ev.acceptProposedAction()
                return

    # ------------------------------------------------------------------
    # Hardware Operations (Arduino Flash, Connect, Detect, Program, etc.)
    # ------------------------------------------------------------------
    def _flash_arduino(self) -> None:
        if self.lane.busy:
            return
        if self.session.connected:
            self._disconnect()
        self.settings.board_key = self.board_key
        cur_port = str(self.cmb_port.currentData() or "")
        if cur_port:
            self.settings.port = cur_port

        dlg = FlashArduinoDialog(self.settings, self.lane, self)

        def _on_flashed(port: str, bkey: str) -> None:
            b_idx = self.cmb_board.findData(bkey)
            if b_idx >= 0:
                self.cmb_board.setCurrentIndex(b_idx)
            self._refresh_ports()
            for i in range(self.cmb_port.count()):
                if self.cmb_port.itemData(i) == port:
                    self.cmb_port.setCurrentIndex(i)
                    break
            self.log(f"Flashed ProgramPic v1.8.horo onto {bkey} ({port}).", "OK")

        dlg.flashed.connect(_on_flashed)
        dlg.exec()
        self._refresh_actions()

    def _connect(self) -> None:
        port = str(self.cmb_port.currentData() or "").strip()
        if not port:
            QMessageBox.information(
                self,
                "Select serial port",
                "Plug in your Arduino programmer and select its serial port first.",
            )
            return
        baud = self.settings.baud
        self.settings.port = port

        def task(progress, _pct, _cancel):
            return self.session.connect(port=port, baud=baud, progress=progress)

        def ok(st) -> None:
            self.progress.setValue(100)
            self.log(
                f"Connected to verified programmer on {st.port} — firmware v{st.firmware} "
                f"({len(st.supported)} devices supported).",
                "OK",
            )
            self.status_lbl.setText("Programmer connected; socket voltage not measured")
            self.apply_theme(self.settings.theme, self.settings.font_size)
            self._refresh_actions()

        self._run_task(task, ok, "Connect Programmer")

    def _disconnect(self) -> None:
        if self.lane.busy:
            return
        self.session.disconnect()
        self.lbl_silicon_probe.setText("Programmer report: disconnected")
        self.status_lbl.setText("Disconnected — verify VPP is off before handling the target")
        self.log(
            "Disconnected from the host. Socket voltage is not measured by this app; verify VPP is off before handling the target.",
            "INFO",
        )
        self.apply_theme(self.settings.theme, self.settings.font_size)
        self._refresh_actions()

    def _detect(self) -> None:
        if not self.session.connected:
            return
        if not self._ensure_preflight():
            return

        def task(progress, _pct, _cancel):
            return self.session.detect_chip(progress=progress)

        def ok(res) -> None:
            info, matched = res
            self.progress.setValue(100)
            if matched is not None:
                self.lbl_silicon_probe.setText(
                    f"ProgramPic reports: {matched.display_name} (raw ID/config not exposed by host)"
                )
                self.log(
                    f"ProgramPic reports {matched.display_name}. The host does not expose raw ID/config values to this app; confirm the package marking and selected target before programming.",
                    "OK",
                )
                idx = self.cmb_mcu.findData(matched.name)
                if idx >= 0 and idx != self.cmb_mcu.currentIndex():
                    ans = QMessageBox.question(
                        self,
                        "Programmer-reported target",
                        f"ProgramPic reports {matched.display_name}, while the selected target is "
                        f"{self.target.display_name}.\n\nSwitch the target selection to "
                        f"{matched.display_name}? The app does not receive raw silicon ID values.",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes,
                    )
                    if ans == QMessageBox.StandardButton.Yes:
                        self.cmb_mcu.setCurrentIndex(idx)
                self.status_lbl.setText(
                    f"Programmer reports {matched.display_name}; socket voltage not measured"
                )
            else:
                label = info.device_name or "unknown"
                self.lbl_silicon_probe.setText(
                    f"ProgramPic reports an unsupported target: {label}; not auto-selected"
                )
                self.log(
                    f"ProgramPic reported unsupported target {label}; destructive operations remain blocked unless a supported target is explicitly selected and independently validated.",
                    "WARN",
                )
                QMessageBox.warning(
                    self,
                    "Unsupported or unidentified target",
                    "The host did not return a supported PIC model. No raw device ID or config word is exposed by the upstream host command. For no-ID devices, select the exact model manually and follow its datasheet; verify wiring and VPP before any destructive action.",
                )

        self._run_task(task, ok, "Auto-Detect PIC")

    def _program(self) -> None:
        if not self.session.connected or self.hex_img is None:
            return
        dev = self.target
        img = self.hex_img
        do_verify = self.settings.auto_verify
        force_cal = not self.chk_preserve_cal.isChecked()

        if not self._ensure_preflight():
            return

        if self.settings.confirm_erase or not do_verify:
            summary = build_summary(
                dev,
                img,
                do_verify=do_verify,
                preserve_calibration=self.chk_preserve_cal.isChecked(),
            )
            fname = Path(self.hex_path).name if self.hex_path else "memory_buffer.hex"
            if not confirm_program(self, dev, fname, summary, do_verify):
                self.log("Programming cancelled by user.", "WARN")
                return

        def task(progress, pct, _cancel):
            return self.session.program_hex(
                img,
                dev,
                progress=progress,
                pct=pct,
                do_verify=do_verify,
                force_calibration=force_cal,
            )

        def ok(summary_text: str) -> None:
            self.progress.setValue(100)
            if do_verify:
                self.log(
                    f"Programming finished — read-back comparison passed for {dev.display_name}.",
                    "OK",
                )
                status = f"Read-back passed for {dev.display_name}"
                title = "Read-back verification passed"
            else:
                self.log(
                    f"Programming command finished for {dev.display_name}; read-back comparison was disabled and not performed.",
                    "WARN",
                )
                status = f"Write finished for {dev.display_name}; verification skipped"
                title = "Programming finished — verification skipped"
            self.status_lbl.setText(status + "; socket voltage not measured")
            QMessageBox.information(
                self,
                title,
                summary_text + "\n\nThe app does not measure socket voltage. Verify VPP is off before handling the target.",
            )

        self._run_task(task, ok, f"Program {dev.display_name}")

    def _verify_only(self) -> None:
        if not self.session.connected or self.hex_img is None:
            return
        dev = self.target
        img = self.hex_img
        force_cal = not self.chk_preserve_cal.isChecked()

        if not self._ensure_preflight():
            return

        def task(progress, pct, _cancel):
            return self.session.verify_hex(
                img,
                dev,
                progress=progress,
                pct=pct,
                force_calibration=force_cal,
            )

        def ok(msg: str) -> None:
            self.progress.setValue(100)
            self.log(msg, "OK")
            self.status_lbl.setText(msg)
            QMessageBox.information(self, "Verification Passed", msg)

        self._run_task(task, ok, f"Verify {dev.display_name}")

    def _blank_check(self) -> None:
        if not self.session.connected:
            return
        dev = self.target
        if not self._ensure_preflight():
            return

        def task(progress, pct, _cancel):
            return self.session.blank_check(dev, progress=progress, pct=pct)

        def ok(res) -> None:
            is_blank, detail = res
            self.progress.setValue(100)
            self.log(detail, "OK" if is_blank else "WARN")
            self.status_lbl.setText(detail)
            QMessageBox.information(self, "Blank Check Result", detail)

        self._run_task(task, ok, f"Blank Check {dev.display_name}")

    def _read_chip(self) -> None:
        if not self.session.connected:
            return
        dev = self.target
        if not self._ensure_preflight():
            return

        def task(progress, pct, _cancel):
            regions = self.session.read_chip(dev, progress=progress, pct=pct)
            flat = {}
            for r in regions.values():
                flat.update(r)
            # Skip read-only Device ID slot when exporting Intel HEX so re-flashing is clean
            return HexImage.from_flat(flat, skip_addrs={dev.config_start + 6})

        def ok(img: HexImage) -> None:
            self.progress.setValue(100)
            self.hex_img = img
            self.hex_path = ""
            self._refresh_hex_summary()
            self._refresh_actions()
            self.circuit_panel.tabs.setCurrentIndex(2)

            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Silicon Readout as Intel HEX",
                f"{dev.name}_backup.hex",
                "Intel HEX (*.hex)",
            )
            if path:
                if not path.lower().endswith(".hex"):
                    path += ".hex"
                Path(path).write_text(img.to_hex(), encoding="utf-8")
                self.hex_path = path
                self._refresh_hex_summary()
                self.log(f"Saved {dev.display_name} readout to {path}", "OK")
                self.status_lbl.setText(
                    f"Saved backup: {Path(path).name}; socket voltage not measured"
                )
            else:
                self.log(
                    f"Read {dev.display_name} into HEX Memory Map buffer (file save skipped).",
                    "INFO",
                )
                self.status_lbl.setText(f"Read {dev.display_name} into memory inspector")

        self._run_task(task, ok, f"Read {dev.display_name}")

    def _erase(self) -> None:
        if not self.session.connected:
            return
        dev = self.target
        preserve = self.chk_preserve_cal.isChecked()
        if not confirm_erase(self, dev, preserve_calibration=preserve):
            self.log("Bulk erase cancelled or blocked by calibration-preservation safety gate.", "WARN")
            return
        if not self._ensure_preflight():
            return

        def task(progress, pct, _cancel):
            return self.session.erase_chip(
                dev,
                preserve_calibration=preserve,
                progress=progress,
                pct=pct,
            )

        def ok(msg: str) -> None:
            self.progress.setValue(100)
            self.log(msg, "OK")
            self.status_lbl.setText(msg)
            QMessageBox.information(self, "Chip Erased", msg)

        self._run_task(task, ok, f"Erase {dev.display_name}")

    # ------------------------------------------------------------------
    # Preferences, Help & Clean Shutdown
    # ------------------------------------------------------------------
    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            b_idx = self.cmb_board.findData(self.settings.board_key)
            if b_idx >= 0:
                self.cmb_board.setCurrentIndex(b_idx)
            m_idx = self.cmb_mcu.findData(self.settings.mcu)
            if m_idx >= 0:
                self.cmb_mcu.setCurrentIndex(m_idx)
            self.log_dock.setVisible(self.settings.log_visible)
            self.apply_theme(self.settings.theme, self.settings.font_size)
            self._refresh_ports()
            self._refresh_actions()

    def _show_info(self) -> None:
        st = self.session.state
        pw = get_pic_wiring(self.target.name)
        bw = get_board_wiring(self.board_key)
        txt = (
            f"Host Arduino Board:  {bw.board_name} ({bw.mcu_label})\n"
            f"Programmer Port:     {st.port or '(disconnected)'}\n"
            f"Programmer Firmware: {st.firmware or '—'}\n"
            f"Host Handshake:      {'Passed' if st.verified else 'Not connected'}\n"
            f"Raw target ID:       Not exposed by host\n"
            f"Socket voltage:      Not measured by app\n\n"
            f"Target PIC MCU:      {self.target.display_name} ({pw.package})\n"
            f"Hardware Mode:       {'ZIF-18 Socket (JP3 = ' + str(pw.jp3_position) + ')' if pw.uses_zif else '6-Wire External ICSP'}\n"
            f"Program Flash:       {self.target.program_words} words (14-bit)\n"
            f"Data EEPROM:         {self.target.data_bytes} bytes\n"
            f"Loaded HEX File:     {self.hex_path or '(none)'}"
        )
        QMessageBox.information(self, "Session & Hardware Summary", txt)

    def _user_guide(self) -> None:
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        else:
            base = Path(__file__).resolve().parents[2]
        guide = base / "docs" / "USER_GUIDE.md"
        if guide.is_file():
            from PySide6.QtWidgets import QDialog, QTextBrowser
            dlg = QDialog(self)
            dlg.setWindowTitle(f"{APP_NAME} — User Guide & Hardware Manual")
            dlg.resize(760, 620)
            v = QVBoxLayout(dlg)
            tb = QTextBrowser()
            tb.setOpenExternalLinks(True)
            tb.setMarkdown(guide.read_text(encoding="utf-8"))
            v.addWidget(tb, 1)
            btn = QPushButton("Close")
            btn.clicked.connect(dlg.accept)
            row = QHBoxLayout()
            row.addStretch()
            row.addWidget(btn)
            v.addLayout(row)
            dlg.exec()
        else:
            QDesktopServices.openUrl(QUrl(ARDPICPROG_URL))

    def closeEvent(self, ev) -> None:  # noqa: N802
        if self.lane.busy:
            ans = QMessageBox.question(
                self,
                "Hardware operation running",
                "A hardware operation is still running.\n"
                "Request cancellation and wait for the host to finish its current command before exiting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                ev.ignore()
                return
            self.session.request_cancel()
            self.lane.cancel()
            worker = self.lane.current
            if worker is not None and not worker.wait(30000):
                QMessageBox.warning(
                    self,
                    "Operation still running",
                    "The hardware command has not finished. The application will stay open rather than force-stop a serial write. Wait for the operation to finish. Before handling the target, independently verify that the external VPP supply is off; this app cannot measure socket voltage.",
                )
                ev.ignore()
                return

        self.session.disconnect()
        self.settings.geometry = self.saveGeometry()
        self.settings.window_state = self.saveState()
        super().closeEvent(ev)
