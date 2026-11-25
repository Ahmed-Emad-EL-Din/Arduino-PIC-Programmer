# Arduino-PIC Programmer

**Windows download:** [Check the project releases](https://github.com/Ahmed-Emad-EL-Din/Arduino-PIC-Programmer/releases).

There is currently no published release or downloadable `.exe` asset in this repository. The previously documented `v2.0.0` URL was broken, so it has been removed instead of being presented as a working download. A Windows build must be published before a direct executable link can be provided.

**Made By:** Ahmed Emad El-Din Hussein · [https://github.com/Ahmed-Emad-EL-Din](https://github.com/Ahmed-Emad-EL-Din)

---

## 1. Hardware Connection & 13V Supply Circuit (LM317 + 24V DC)

### Required Components
*   **Arduino Board:** Uno / Nano / Pro Mini / Mega / Leonardo / Micro
*   **Target PIC MCU:** PIC16F84A (default) or 24 other supported MCUs (PIC12F675, PIC16F877A, etc.)
*   **24V DC Power Supply** (Input)
*   **LM317 Voltage Regulator Circuit** (Output: 13V VPP + 5V VDD)
*   **ZIF-18 Socket** (or ICSP Header for 14/20/28/40-pin MCUs)
*   **Wiring:** D2→VDD, D3→MCLR/VPP, D4→CLK, D5→DATA, /RESET→2.2µF Cap→GND

### 13V VPP Supply Diagram (LM317 + 24V DC)
![LM317 13V VPP Circuit](image-search/lm317-13v-vpp-circuit-diagram-24v-dc-sup-1.jpg)
*Values: R1 = 120Ω, R2 = 2.2kΩ (Output ≈ 13V VPP), Input = 24V DC, Output Capacitor = 100nF, Pull-up = 10kΩ, PGM Pull-down = 4.7kΩ.*

### Wiring notes for supported PIC packages
The generated workbench screenshots previously referenced here are not included in this checkout. The physical reference image above is the only circuit image currently provided.

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
4. Press **Flash Firmware** if the firmware files and `avrdude` are available in your build.
5. Confirm success only after the uploader reports that ProgramPic firmware was uploaded.

> This checkout does not contain firmware files or a published Windows executable, so the described flash flow cannot be run from this snapshot as-is.

### Step 2 — Connect & Verify
1. Connect Arduino to PC. Connect 24V DC to LM317 circuit.
2. Select Board and COM Port in the app.
3. Press **Connect Programmer** (`Ctrl+P`).
4. Status chip turns **Green (Programmer: ✓ vX)** — Handshake passed.

### Step 3 — Load HEX & Select MCU
1. **Open HEX…** (`Ctrl+O`) or drag-and-drop `.hex` file.
2. Pick Target MCU (e.g., **PIC16F84A**) from dropdown.
3. **Detect Chip** (`F6`) — verifies Device ID matches selection.

### Step 4 — Preflight & Programming
1. **Preflight Checklist** appears (VPP LED, Socket, Jumper, Voltage). Tick all items.
2. **Confirmation Dialog** shows exact operation (Erase → Write → Verify → Safe State).
3. Press **Program & Verify** (`Ctrl+R`).
4. **Activity Log** tracks progress:
   ```
   Step 1/5 — verify chip identity … Detected: PIC16F84A … identity OK
   Step 2/5 — erase chip …
   Step 3/5 — write program memory …
   Step 4/5 — READ BACK & VERIFY … ✓ verify passed
   Step 5/5 — power off socket (safe state) …
   ```
5. **SUCCESS** dialog appears.

### Step 5 — Other Operations
*   **Erase Only…** — bulk erase with calibration preservation.
*   **Verify vs File** — read chip and compare against loaded HEX.
*   **Read Chip → Save HEX…** (`Ctrl+S`) — backup chip to Intel HEX.
*   **Device Info** — port, firmware version, device ID, config word.

---

## 3. Safety Interlocks (intended behavior)

These safeguards are described by the application design. This checkout is incomplete and cannot currently be run to verify them; always verify hardware wiring and firmware independently.
| Gate | Behaviour |
|---|---|
| Programmer verified | Handshake required before any command |
| Device-ID match | Chip ID must equal selected MCU (mask `0xFFE0`) |
| Empty socket / no VPP | ID `0x3FFF` or unreadable chip → refused |
| No-ID chips (PIC16F84) | Explicit warnings + forced `SETDEVICE` map |
| HEX fit check | HEX must only touch existing regions |
| Preflight checklist | VPP LED, socket, jumper, voltage — all items ticked |
| Confirmations | Erase/program dialogs spell out exact actions |
| Verify after write | ON by default; extra confirmation to disable |
| Safe state | `PWROFF` after every operation, errors, cancel, close |
| Firmware safety net | ProgramPic auto power-offs after 2s inactivity |

---

## 4. Supported Targets (25 MCUs)
`PIC16F84A` (default), PIC16F84, PIC16F627/A, PIC16F628/A, PIC16F648A,
PIC16F630, PIC16F676, PIC16F684, PIC16F688, PIC16F690, PIC16F87, PIC16F88,
PIC16F872, PIC16F877/A, PIC16F882–887, PIC12F629, PIC12F675, PIC12F683.

---

## 5. Requirements
* **Windows 10/11:** no Windows executable is currently published.
* **Arduino Board** + **LM317 13V Circuit** + **ZIF/ICSP Shield** for hardware use.
* **24V DC Supply** (as used in the circuit image above; verify your exact circuit design).
* Firmware and `avrdude` are not present in this checkout.

---

## 6. Project Layout (files present in this checkout)
```
├── plain.md                  # repair checklist
├── src/core/                 # MCU database and safety logic only
├── src/gui/                  # main window and widgets only
├── src/tests/                # GUI integration tests
├── packaging/                # PyInstaller spec (referenced input folders are absent)
├── docs/                     # user guide
└── image-search/             # LM317 circuit image
```

This is not a complete runnable/buildable application snapshot: several modules imported by the GUI, application entry point, firmware, assets, and build workflow are missing.

---

## 7. Credits & License
* **Author:** Ahmed Emad El-Din Hussein · [https://github.com/Ahmed-Emad-EL-Din](https://github.com/Ahmed-Emad-EL-Din)
* **Firmware reference:** ProgramPic v1.8.horo (Ho-Ro/ArdPicProg)
* **License:** No `LICENSE` file is included in this checkout; confirm licensing before redistribution.

---

## 8. Disclaimer
High-voltage (≈13 V) programming circuitry is involved. The author assumes
no responsibility for damaged chips, boards, or injury. Always verify
wiring, VPP supply, and device selection before programming.
