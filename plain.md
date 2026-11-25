# Arduino-PIC-Programmer — Project Plan (`plain.md`)

**Goal:** A professional, modern, reliable, hardware-safe desktop **Windows EXE** (`Arduino-PIC-Programmer.exe`) that:
1. Flashes `ProgramPic` (v1.8.horo) programmer firmware onto an Arduino (Uno, Nano old/new bootloader, Pro Mini 16/8 MHz, Mega 2560, Leonardo, Micro),
2. Verifies the Arduino is a ready-to-use PIC programmer (handling DTR auto-reset vs 2.2 µF reset-cap vs native USB),
3. Uploads `.hex` files to **PIC16F84A** and all 24 other supported PIC MCUs safely — zero-tolerance for hardware damage,
4. Renders an **exact, dynamic, IEEE-standard circuit schematic** (`schemdraw` SVG + official `Ho-Ro/ArdPicProg` reference schematic & hardware photo) tailored to the **currently selected Arduino board AND target PIC MCU** (DIP package, exact pin numbers, ZIF socket insertion alignment, JP3 jumper position, or ICSP wiring),
5. Delivers a crafted, **unslopped** desktop engineering workbench UX (applying `heydamir/unslop`, `m0rphMZ/unslop-design-skill`, and `TheQtCompanyRnD/qt-ui-design`),
6. Builds and publishes a ready-to-run standalone **Windows x64 `.exe`** (with bundled `avrdude.exe` + `avrdude.conf` + precompiled Arduino firmware).

**Credits:** Made By: **Ahmed Emad El-Din Hussein** · <https://github.com/Ahmed-Emad-EL-Din>

---

## PHASE 0–6 — Foundation (Restored from Backup & Verified)
- [x] 0.1 Restore full project backup from Google Drive & study `Ho-Ro/ArdPicProg`, `rweather/ardpicprog`, `Ho-Ro/QPICkit`
- [x] 0.2 Gather & study best UI/UX & engineering skills (`heydamir/unslop`, `unslop-design-skill`, `qt-ui-design`, `schemdraw`)
- [x] 0.3 Verify baseline test suite (32/32 passing)

---

## PHASE 7 — Core Engine Audit, Bug Fixes & Hardware-Safety Hardening
- [x] 7.1 **Fix `ERASE` without prior `DEVICE` bug**: always probe & verify target MCU identity (`gate_device_match` / `SETDEVICE`) before sending `ERASE` so firmware never uses stale PIC16F628A default flash algorithm on a PIC16F84A/PIC16F877A
- [x] 7.2 **Preserve factory calibration (`OSCCAL` / BG bits)**: skip `reserved_start..reserved_end` words during program write & read-back verify unless `force_calibration` is explicitly enabled (preventing loss of factory calibration on PIC12F629/675, PIC16F630/676, PIC16F690)
- [x] 7.3 **Fix write order for Code Protection safety**: write Program → EEPROM Data → Config Fuses last (matching reference `ardpicprog` host so CP/CPD fuses never block EEPROM write/verify)
- [x] 7.4 **Fast binary protocol (`READBIN` / `WRITEBIN`) + `PENDING` support**: implement binary packet transfer with automatic `WRITE` fallback for 10-byte (`0x0A` LF) packets and `PENDING` timeout extension, cutting programming/verify time by ~5–8×
- [x] 7.5 **Fix full-chip `blank_check` & `read_chip` device init**: probe/select device first, check full program + EEPROM memory (skipping reserved OSCCAL), and guarantee `PWROFF` in `try/finally` across every operation
- [x] 7.6 **Smart serial handshake & DTR reset handling**: handle boards with 2.2 µF reset cap (instant response), Uno/Nano/Mega auto-reset, and Leonardo/Micro native USB CDC without false timeouts; validate odd-byte Intel HEX records cleanly
- [x] 7.7 **Complete MCU pinout & hardware wiring database (`pinout_db.py`)**: exact Microchip datasheet PDIP pin counts, ICSP pins (`MCLR/VPP`, `VDD`, `VSS`, `PGD/DATA`, `PGC/CLK`, `PGM`), ZIF-18 placement & JP3 jumper state vs ICSP-only adapter mode, plus Arduino board pin/reset metadata

---

## PHASE 8 — Dynamic Standard Circuit Schematic & Pinout Visualizer
- [x] 8.1 **Bundle official `Ho-Ro/ArdPicProg` reference assets**: `ArdPicProg_1_8_horo.png` schematic and `ArdPicProg.jpg` build photo in `assets/reference/`
- [x] 8.2 **Build IEEE/IEC standard schematic generator (`src/core/circuit_drawer.py`)**: use `schemdraw` to draw crisp, dimensionally accurate vector schematics (SVG, dark & light themes) showing the 13 V VPP stage (JP1, D1, LED+10k, Q1A/Q1B BC548 NPN switches), Arduino board pins (`D2 VDD` + 100nF, `D3 MCLR`, `D4 CLK`, `D5 DATA`, `/RESET` 2.2 µF cap), and the exact target connection:
  - **ZIF-18 Direct Mode** (8-pin & compatible 18-pin PICs): draws 18-pin ZIF socket, highlights JP3 (`1-2` for 18-pin, `2-3` for 8-pin), 4.7k PGM pull-down, and exact chip seating
  - **ICSP Cable / Adapter Mode** (14-pin, 20-pin, 28-pin, 40-pin, and PIC16F87/88): draws 6-pin ICSP header + target PIC DIP IC symbol with exact datasheet pin numbers (`VDD`, `VSS`, `MCLR/VPP`, `PGD`, `PGC`, `PGM` 4.7k pull-down, 100nF decoupling)
- [x] 8.3 **Build interactive DIP IC & ZIF-18 Socket Pinout Widget (`src/gui/widgets/circuit_panel.py`)**: live zoomable schematic viewer, DIP package pinout diagram with Pin-1 notch & color-coded ICSP signal badges, ZIF-18 lever/slot placement diagram, wiring connection table, and toggleable Official Reference Schematic / Hardware Photo tabs

---

## PHASE 9 — UX "Unslop" Redesign (Professional Desktop Workbench)
- [x] 9.1 **Unslop Design System (`src/gui/theme.py` & `icons.py`)**: apply `heydamir/unslop` + `unslop-design-skill` + `qt-ui-design`:
  - Neutral graphite/ink ramp (`#0f1115` / `#161920` / `#1d212b` dark; `#f6f7f9` / `#ffffff` light), hairlines, 4px spacing grid, concentric border radii (`inner = outer - padding`)
  - Single purposeful accent, tabular numerals for addresses/counters, zero shouty uppercase filler pills, crisp 1.6px uniform stroke SVG icons (theme-aware)
- [x] 9.2 **Two-Column Desktop Workbench Layout (`src/gui/main_window.py`)**:
  - Top status header bar with real hardware state indicators (Arduino Board, Programmer Link, Target MCU, HEX Image) + primary toolbar
  - **Left Pane**: Clean, scannable workflow sections (1. Programmer Setup & Connection · 2. Firmware Image & Memory Map usage bars · 3. Target MCU & Silicon Operations including Detect, Program & Verify, Verify, Read Backup, Blank Check, Erase)
  - **Right Pane**: Live **Hardware Wiring & Circuit Inspector** (`Dynamic Circuit Schematic` · `IC Pinout & ZIF Placement` · `HEX Memory Inspector` · `Official ArdPicProg Reference`) updating instantaneously whenever Arduino board or Target MCU changes
  - **Bottom Dock**: Filterable, timestamped monospace Activity Log + progress bar with stage indicator & instant Cancel
- [x] 9.3 **Polish all dialogs (`FlashArduinoDialog`, `PreflightDialog`, `SettingsDialog`, `AboutDialog`)**: dynamic preflight checklist items tailored to the chosen MCU (e.g. exact JP3 position or ICSP PGM pin note), board-specific reset hints, and clean layout

---

## PHASE 10 — Comprehensive Testing & QA
- [x] 10.1 Expand unit & integration test suite (`src/tests/`): test binary `READBIN`/`WRITEBIN` (incl. `0x0A` packet edge case), calibration preservation, CP-safe write order, erase-before-device safety gate, all 25 MCU pinout/wiring rules, SVG schematic generation for every board × MCU family, and offscreen Qt GUI tests
- [x] 10.2 Run offscreen GUI rendering & capture high-DPI screenshots (dark & light themes, ZIF-18 mode & ICSP 40-pin mode, Pinout tab) and visually inspect every screen with `read_file` to verify zero visual defects or slop

---

## PHASE 11 — Standalone Ready-to-Work Windows `.exe` Packaging & Release
- [x] 11.1 Update `packaging/ardpicprog.spec`, `packaging/build.bat`, `packaging/build.sh`, and `.github/workflows/build-windows.yml` to produce **both** a single-file portable `Arduino-PIC-Programmer.exe` (with bundled Windows `avrdude.exe` + `avrdude.conf` + firmware `.hex` + reference schematics) and a distributable `.zip`, plus Linux binary verification
- [x] 11.2 Commit, push to branch `arena/10056028-arduino-pic-programmer`, trigger GitHub Actions Windows x64 build (or verify workflow), download/verify built `.exe` artifact, and update documentation (`README.md`, `docs/USER_GUIDE.md`, `CHANGELOG.md`)
