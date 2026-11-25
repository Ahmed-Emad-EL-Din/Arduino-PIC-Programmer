# Arduino-PIC Programmer — User Guide

**Made By: Ahmed Emad El-Din Hussein** ·
<https://github.com/Ahmed-Emad-EL-Din>

---

## 1. Hardware you need

Follow the reference circuit (official Ho-Ro schematic):
**[https://github.com/Ho-Ro/ArdPicProg/blob/master/ArdPicProg_1_8_horo.png](https://github.com/Ho-Ro/ArdPicProg/blob/master/ArdPicProg_1_8_horo.png)**

* An Arduino (Uno / Nano / Pro Mini / Mega / Leonardo) + USB cable
* The ArdPicProg shield (13 V VPP supply + ZIF socket + ICSP header)
  — or the equivalent wiring:
  * **D2 → VDD**, **D3 → MCLR/VPP**, **D4 → CLK**, **D5 → DATA**
    (ProgramPic v1.8.horo pinout)
  * External **16–20 V** input for the 13 V VPP rail (red LED = VPP OK)
* The target PIC (e.g. PIC16F84A) in the ZIF socket, pin 1 aligned,
  lever locked
* Jumper **JP3**: position 1-2 for 18-pin chips (PIC16F84A),
  2-3 for 8-pin chips (PIC12F675)

## 2. First-time setup (once)

### Step 1 — Flash Arduino Firmware…
1. Menu **Programmer → Flash Arduino Firmware…**
2. Pick your board (e.g. *Arduino Uno (ATmega328P)*) and the COM port
   (use **Rescan** after plugging in).
3. Press **Flash Firmware** and confirm. Keep USB connected.
   * If upload fails: Nano → try *Old Bootloader* variant;
     Leonardo/Micro → press reset twice when prompted.
4. `avrdude` is bundled in the Windows `.exe` release (no manual install).
   (Linux/macOS users: install via package manager or download from
   [https://github.com/avrdudes/avrdude/releases](https://github.com/avrdudes/avrdude/releases).)

### Step 2 — Connect & verify
1. Home page **Step 2 → Connect** (or `Ctrl+P`).
2. The status chip turns green **Programmer: ✓ vX** — the handshake
   passed. If it fails, close the Arduino Serial Monitor and retry.

## 3. Every-day programming flow

| Step | Action | Shortcut |
|---|---|---|
| 3 | **Open HEX…** (drag & drop also works) | `Ctrl+O` |
| 4 | Pick the **target MCU** (default PIC16F84A), press **Detect Chip** | `F6` |
| 5 | Press **Program Chip** | `Ctrl+R` |

Then:

1. **Preflight checklist** appears once per session — tick every item
   (VPP LED, socket, jumper, voltage).
2. **Confirmation** shows exactly what will happen
   (erase → write → verify → safe state). Read it, then continue.
3. Watch the progress bar and Activity Log:
   ```
   Step 1/5 — verify chip identity …     Detected: PIC16F84A … identity OK
   Step 2/5 — erase chip …
   Step 3/5 — write program memory …
   Step 4/5 — READ BACK & VERIFY …       ✓ verify passed
   Step 5/5 — power off socket (safe state) …
   ```

The dialog ends with **SUCCESS** only after verification passes.

## 4. Other operations (Programmer menu)

* **Erase Only…** — bulk erase with calibration/ID preservation.
* **Verify vs File** — read the chip and compare against the loaded HEX
  without writing.
* **Read Chip → Save HEX…** — backup the chip to an Intel HEX file
  (`Ctrl+S`).
* **Device / Programmer Info** — port, firmware version, device ID,
  config word, identity-verification status.

## 5. Menus overview

* **File** — Open HEX, Open Recent, Save Read Image As…, Export Log…, Exit
* **Programmer** — Detect Ports (`F5`), Flash Arduino Firmware…,
  Connect/Disconnect (`Ctrl+P`), Detect Chip (`F6`), Device Info,
  Erase…, Program… (`Ctrl+R`), Verify, Read
* **Settings** — Connection (port/baud/board/MCU), Appearance
  (dark/light, font size), Safety (confirmations, auto-verify)
* **View** — Show Log (`Ctrl+L`), Zoom In/Out (`Ctrl +/-`), Reset,
  Toggle Theme (`Ctrl+T`)
* **Help** — User Guide, Wiring Diagram, ProgramPic Firmware Help,
  QPICkit, Check for Updates, About

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| “No response from the Arduino” | Wrong port / firmware missing / Serial Monitor open | Rescan ports, flash firmware, close Serial Monitor |
| “avrdude failed — not in sync” | Wrong board variant or port | Try Nano *Old Bootloader*; press reset and retry |
| `DEVICE failed` | Empty socket, VPP off, chip backwards | Check red VPP LED, pin-1 orientation, lever |
| “Chip reports X but Y is selected” | Wrong MCU selected or wrong chip | The write is **blocked** — fix the selection/chip |
| Verify failed after write | Unstable VPP, bad chip, wiring | Check 13 V supply/wiring; try another chip |
| Port busy / access denied | Another program using the port | Close MPLAB/QPICkit/Serial Monitor |
| HEX “outside memory map” | HEX from a different MCU | Load the HEX built for your selected target |

## 7. Safety notes

* The 13 V VPP supply must never be plugged into the Arduino power jack.
* Do not touch the ZIF/ICSP contacts while programming.
* The app forces **safe state (PWROFF)** after every operation, on
  errors, on cancel, and when it closes.
* ProgramPic itself auto-power-offs after 2 s without host activity —
  even if the PC crashes mid-operation.
