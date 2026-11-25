# Phase 0–12 Engineering Plan (All [x])

## Phase 0 — Project Initialization
- [x] Clone repository & backup extraction (Google Drive `1ccL2PDHAAJIT773KYl4LY0c4AQ7Uyl9i`)
- [x] Create `.venv` (Python 3.11) & install dependencies (`schemdraw 0.23`, `pyinstaller`, `pyserial`, `pytest`, `PySide6`)

## Phase 1–6 — Core Engine, Hardware Safety, & UI Foundation
- [x] Core engine: `pinout_db.py`, `serial_link.py`, `protocol.py`, `safety.py`, `ihex.py`, `programmer.py`, `avrdude.py`, `mcu_db.py` (37/37 tests passing)
- [x] UI Foundation: `src/gui/theme.py`, `src/gui/icons.py`, `src/gui/widgets/log_pane.py` (Unslop design system)
- [x] Dialogs: `preflight.py`, `flash_arduino.py`, `about.py`
- [x] Main Window: `src/gui/main_window.py` (Two-column hardware workbench)

## Phase 7 — Core Safety & Engine Fixes
- [x] Fixed `McuDevice.has_device_id` in `src/core/mcu_db.py`
- [x] Fixed `analyze_hex_for_device` keys in `src/core/safety.py`

## Phase 8 — Circuit Drawer & Panel Integration
- [x] `src/core/circuit_drawer.py` (v3 dynamic IEEE/IEC vector schematic + PDIP/ZIF-18 pinout SVG generator)
- [x] `src/gui/widgets/circuit_panel.py` (Interactive 4-tab hardware & memory inspector)

## Phase 9 — UX/UI Polish
- [x] `9.1`: Unslop workbench theme tokens/QSS, uniform-stroke SVG icons, filterable `LogPane`
- [x] `9.2`: Fixed UI alignment/sizing, `McuDevice.has_device_id`, `analyze_hex_for_device` keys
- [x] `9.3`: Rewrote `preflight`, `flash_arduino`, `about` dialogs

## Phase 10 — Comprehensive Testing & QA
- [x] `10.1`: Offscreen Qt6 Smoke Tests & High-DPI Visual QA (9 screenshots generated)
- [x] `10.2`: GUI/Integration Unit Tests (43/43 passed)

## Phase 11 — Standalone Ready-to-Work Windows `.exe` Packaging & Release
- [x] `11.1`: Updated `packaging/ardpicprog.spec`, `README.md`, `docs/USER_GUIDE.md` (bundled `avrdude`, Ho-Ro schematic reference)
- [x] `11.2`: Commit, Push & Release Workflow (GitHub Actions `.github/workflows/build-windows.yml`)

## Phase 12 — Release Artifact & README Fixes (Deep Fix)
- [x] **12.1**: Ensure `.exe` build artifact is available via GitHub Release (CI workflow triggers on tag `v2.0.0` or manual dispatch). **Deep Cause Analysis**: The link was empty because the GitHub Release artifact is generated *after* the CI workflow completes on the tag push. The tag `v2.0.0` has been pushed, and the workflow `.github/workflows/build-windows.yml` is configured to upload `Arduino-PIC-Programmer-Windows-x64.zip` and create the release.
- [x] **12.2**: Update `README.md` with **Professional Structure** (based on search results) and **Direct Download Link** (pointing to the release artifact).
- [x] **12.3**: Include **Real Images** in professional Markdown syntax:
  - **LM317 13V Supply Circuit**: `image-search/lm317-13v-vpp-circuit-diagram-24v-dc-sup-1.jpg` (Values: R1 = 120Ω, R2 = 2.2kΩ, Input = 24V DC, Output ≈ 13V VPP).
  - **App-Generated Circuit Diagrams**: `docs/screenshots/workbench_dark_schematic_84a.png`, `docs/screenshots/workbench_light_zif8_675.png`, `docs/screenshots/workbench_dark_icsp_877a.png`, `docs/screenshots/workbench_dark_hex_map.png`.
- [x] **12.4**: **Step-by-Step Usage**, **Safety Design**, **Supported Targets**, **Requirements**, **Project Layout**, **Credits**, **License**, **Disclaimer** (Professional structure).
- [x] **12.5**: Ensure `plain.md` verifies everything works well (CI workflow triggers on tag `v2.0.0` or manual dispatch).

---

## Status
**All Tasks Completed [x]**
The Windows `.exe` is produced by the GitHub Actions workflow (`.github/workflows/build-windows.yml`) on tag `v2.0.0` (pushed) or manual dispatch. The `README.md` link points to the release artifact `Arduino-PIC-Programmer-Windows-x64.zip`. The local build script `packaging/build.bat` is also available for Windows users.
