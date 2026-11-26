# Arduino-PIC Programmer

## Windows build status

**Installable Windows package:** after this branch's updated Windows workflow passes, open the [Windows desktop package workflow](https://github.com/Ahmed-Emad-EL-Din/Arduino-PIC-Programmer/actions/workflows/build-windows.yml), select that successful run, and download **Arduino-PIC-Programmer-Windows-x64-candidate**. The previously passing workflow run predates installer packaging and does not contain a setup executable. Extract GitHub's outer artifact ZIP. The updated artifact will contain an installer, the portable ZIP, and a SHA-256 sidecar for each. Verify the installer before running it:

```powershell
$setup = 'Arduino-PIC-Programmer-Setup-x64.exe'
$expected = ((Get-Content ($setup + '.sha256') -Raw).Trim() -split ' +')[0].ToLowerInvariant()
$actual = (Get-FileHash -Path $setup -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw 'SHA-256 mismatch; do not install this file.' }
```

The installer performs a per-user install, adds a Start menu shortcut, and registers an uninstaller; it does not require administrator rights. The portable ZIP remains available as an alternative and contains only the app executable plus its required `_internal` runtime bundle—no source tree, firmware source, build tools, or CI reports. Keep `_internal` beside the EXE when extracting it. The same run also uploads short-lived real UI screenshots for review.

These will be temporary Actions artifacts (14-day retention; GitHub sign-in/repository access may be required), **not a published GitHub Release**. If they expire, run the workflow manually for the desired branch.

### Why Windows may show “Windows protected your PC”

That dialog is Microsoft Defender SmartScreen's **publisher/file-reputation** warning. It commonly appears for a new, unsigned download; it is not by itself a malware detection. Packaging the EXE inside an installer or ZIP does not remove the warning. This workflow signs the app binaries and installer only for version-tag builds when a trusted Authenticode certificate is configured through protected GitHub Actions secrets. Without that signing setup, the candidate is unsigned and SmartScreen may warn. Even a valid signature does not guarantee an immediate warning-free first release: reputation builds over time, and EV certificates no longer bypass SmartScreen. Microsoft identifies Microsoft Store distribution as the reliable way to avoid SmartScreen download warnings; that distribution path is not set up for this project yet. See [Microsoft's SmartScreen guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).

Do not disable SmartScreen or bypass its warning for this unvalidated candidate. Verify the source and SHA-256; wait for a signed, hardware-validated release before installing it for programming work.

**Not yet a validated release:** the updated installer workflow has not run yet. Once it does, it will build and smoke-test the installer, but that still will not replace clean-PC testing or physical programmer hardware validation. Do not use this candidate for destructive programming until the Windows and hardware acceptance steps below pass. The [Releases page](https://github.com/Ahmed-Emad-EL-Din/Arduino-PIC-Programmer/releases) does not yet contain a validated downloadable release.

**Made By:** Ahmed Emad El-Din Hussein · [https://github.com/Ahmed-Emad-EL-Din](https://github.com/Ahmed-Emad-EL-Din)

---

## 1. Hardware connections and VPP supply reference

### Required hardware
- **Arduino:** Uno, Nano, Mega, Leonardo/Micro, or 5 V / 16 MHz Pro Mini. The 3.3 V Pro Mini is not electrically compatible.
- **Target PIC:** one of the supported devices; confirm its exact package and pinout in the device datasheet.
- **Programmer interface:** ArdPicProg shield or equivalent ZIF/ICSP wiring. D2=VDD, D3=MCLR/VPP, D4=CLK, D5=DATA. Some boards need the reset capacitor noted in the board-specific wiring reference.
- **VPP supply:** use the supply specified by the exact programmer hardware. The LM317 drawing below is a calculation/reference circuit, not a validated substitute for the official ArdPicProg shield. The user guide's official shield reference calls for a 16–20 V input; do not apply 24 V to that shield unless its documentation explicitly permits it.

### LM317 reference circuit: 24 V DC to approximately 13 V VPP

![Reference-only LM317 circuit for approximately 13 V VPP from 24 V DC](docs/images/lm317-24v-to-13v-vpp.svg)

This is the standard LM317 adjustable-regulator topology: R1=120 Ω from OUT to ADJ and R2=1.12 kΩ from ADJ to common, giving approximately 13.0 V nominal from the LM317 equation. It shows a 0.1 µF input bypass capacitor and 1 µF output capacitor. The output is **VPP only**; target VDD is a separate programmer rail, not another LM317 output. Use a regulated, current-limited 24 V DC source, a suitable heatsink, and check the output with a meter before connecting a target. Regulator dissipation depends on load (approximately (24−13) × load current). Actual output, current capacity, thermal performance, protection, and compatibility with a particular programmer have not been validated here. Do not use this reference to build or operate hardware for destructive programming without independent design review and bench testing.

### Wiring notes for supported PIC packages
Official Ho-Ro reference images are bundled in `assets/reference/`. The desktop inspector's generated view is an illustrative wiring overview, not an electrical schematic; use the official reference and exact device datasheet to confirm connections. Unverified pin mappings are flagged.

**A. ZIF-18 Direct Mode (8-pin & 18-pin PICs)**
*   **PIC16F84A (18-pin):** JP3 = `1-2`. Pins: VDD=14, VSS=5, MCLR=4(RA5), PGC=12(RB6), PGD=13(RB7), PGM=10(RB4).
*   **PIC12F675 (8-pin):** JP3 = `2-3`. Pins: VDD=1, VSS=8, MCLR=4(GP3), PGC=6(GP1), PGD=7(GP0).

**B. ICSP Cable / Adapter Mode (14/20/28/40-pin PICs)**
*   **PIC16F877A (40-pin):** ICSP Header. Pins: VDD=11&32, VSS=12&31, MCLR=1, PGC=39(RB6), PGD=40(RB7), PGM=36(RB3).

The HEX memory-map inspector is an application feature; no screenshot is included in this repository snapshot.

---

## 2. Step-by-Step Usage

### Step 1 — Flash Arduino Firmware (Once)
1. Launch **Arduino-PIC-Programmer.exe**.
2. Menu **Programmer → Flash Arduino Firmware…**
3. Pick board (e.g., *Arduino Uno*) and COM port.
4. Press **Flash Firmware** in a build that contains the matching precompiled firmware and bundled `avrdude`.
5. Confirm success only after the uploader reports that ProgramPic firmware was uploaded.

> The candidate is a temporary Actions artifact, not a published release. Leonardo/Micro firmware upload in this app is unsupported; use Arduino IDE for those boards.

### Step 2 — Connect & Verify
1. Connect the Arduino by USB. Only connect an external VPP supply that matches the exact programmer hardware; the reference LM317 circuit above is not hardware-validated.
2. Select Board and COM Port in the app.
3. Press **Connect Programmer** (`Ctrl+P`).
4. Status chip turns **Green (Programmer: ✓ vX)** — Handshake passed.

### Step 3 — Load HEX & Select MCU
1. **Open HEX…** (`Ctrl+O`) or drag-and-drop `.hex` file.
2. Pick Target MCU (e.g., **PIC16F84A**) from dropdown.
3. **Detect Chip** (`F6`) — asks the ProgramPic host to identify a supported device. The raw ID/config values are not exposed by the upstream CLI; every destructive operation re-asks the host to validate the selected device.

### Step 4 — Preflight & Programming
1. **Preflight Checklist** appears (VPP LED, Socket, Jumper, Voltage). Tick all items.
2. **Confirmation Dialog** shows exact operation (Erase → Write → Verify → Safe State).
3. Press **Program & Verify** (`Ctrl+R`).
4. The Activity Log shows the upstream host's erase/write/read output, followed by a read-back comparison for every supplied address. The host closes its serial port on exit and sends its documented `PWROFF` command.
5. A success message appears only if the host operation and configured read-back verification pass.

### Step 5 — Other Operations
*   **Erase Only…** — bulk erase with calibration preservation.
*   **Verify vs File** — read chip and compare against loaded HEX.
*   **Read Chip → Save HEX…** (`Ctrl+S`) — backup chip to Intel HEX.
*   **Device Info** — port, firmware version, selected target, package and memory sizes. The upstream CLI does not expose raw ID/config values to this window.

---

## 3. Safety Interlocks (intended behavior)

The source implements these gates, but it has not yet been validated on physical programmer hardware. Always confirm the exact MCU datasheet, wiring, and VPP supply independently; do not use an untested build for destructive operations.
| Gate | Behaviour |
|---|---|
| Programmer verified | Handshake required before any command |
| Device selection | Host detection is requested, but raw silicon ID/config values are not exposed to the GUI; do not treat a displayed model as a measured ID |
| Empty socket / no VPP | Host detection errors may be surfaced; physical empty-socket/VPP failure behavior is not hardware-validated |
| No-ID chips (PIC16F84) | Manual target-selection warning; electronic identity cannot distinguish devices with no silicon ID |
| HEX fit check | HEX must only touch existing regions |
| Preflight checklist | VPP LED, socket, jumper, voltage — all items ticked |
| Confirmations | Erase/program dialogs spell out exact actions |
| Verify after write | ON by default; extra confirmation to disable |
| Safe state | Upstream host sends its documented `PWROFF` during normal shutdown; abnormal process termination and physical safe-state behavior still need hardware validation |
| Firmware safety net | Upstream firmware documents an inactivity power-off; this behavior has not been validated in this application's hardware acceptance tests |

---

## 4. Supported Targets (25 MCUs)
`PIC16F84A` (default), PIC16F84, PIC16F627/A, PIC16F628/A, PIC16F648A,
PIC16F630, PIC16F676, PIC16F684, PIC16F688, PIC16F690, PIC16F87, PIC16F88,
PIC16F872, PIC16F877/A, PIC16F882–887, PIC12F629, PIC12F675, PIC12F683.

---

## 5. Requirements
* **Windows 10/11:** a temporary CI candidate artifact is available above; no validated Windows executable has been published as a GitHub Release.
* **Arduino Board** + **LM317 13V Circuit** + **ZIF/ICSP Shield** for hardware use.
* **24V DC Supply** (as used in the circuit image above; verify your exact circuit design).
* Firmware source is in `firmware/source/`; Windows build scripts compile board-specific firmware and stage `avrdude` for the portable package.
* A Windows executable has not yet been published; build results must pass the Windows and hardware acceptance checklist before release.

---

## 6. Project Layout
```
├── app/                      # application identity and persistent settings
├── src/main.py               # desktop entry point
├── src/core/                 # HEX, safety, wiring, serial-host adapter
├── src/gui/                  # Qt workbench, dialogs, workers, inspectors
├── src/tests/                # integration and core regression tests
├── firmware/source/          # upstream ProgramPic Arduino sketch
├── vendor/ArdPicProg/        # upstream GPL-3.0 host implementation
├── packaging/                # PyInstaller and Windows build scripts
├── .github/workflows/        # Windows candidate-package workflow
└── docs/                     # user guide and hardware notes
```

The Windows candidate workflow has passed; a clean-machine launch and physical-device acceptance tests remain outstanding. No validated release asset is published yet.

---

## 7. Credits & License
* **Author:** Ahmed Emad El-Din Hussein · [https://github.com/Ahmed-Emad-EL-Din](https://github.com/Ahmed-Emad-EL-Din)
* **Firmware and host protocol:** ProgramPic v1.8.horo / ArdPicProg (Ho-Ro / Southern Storm Software), GPL-3.0; see [`LICENSE`](LICENSE) and `vendor/ArdPicProg/UPSTREAM.md`.
* **Python GUI:** project source in this repository; see `LICENSE` for distribution terms.

---

## 8. Disclaimer
High-voltage (≈13 V) programming circuitry is involved. The author assumes
no responsibility for damaged chips, boards, or injury. Always verify
wiring, VPP supply, and device selection before programming.
