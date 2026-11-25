# Arduino-PIC Programmer — User Guide

**Made By: Ahmed Emad El-Din Hussein** ·
<https://github.com/Ahmed-Emad-EL-Din>

---

## Status: source/build candidate, not a validated release

There is no downloadable Windows executable yet. The Windows workflow has not completed in this project, and no physical hardware validation has been performed. Treat the UI/workflow descriptions below as intended candidate behavior, not as a guarantee that programming is ready for use. Do not perform destructive programming with an unvalidated build.

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
   * If Nano upload fails, select the *Old Bootloader* variant.
   * Leonardo/Micro firmware upload is not implemented in the app yet because these boards re-enumerate their bootloader COM port; use Arduino IDE for that upload flow.
4. The source pipeline includes a Windows script that compiles supported board firmware and stages `avrdude` for packaging. This pipeline has not yet been validated on Windows and does not provide a downloadable application today.

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

1. Review the hardware preflight prompts and confirm the physical VPP supply, target orientation, wiring, and jumper independently.
2. Confirm the operation only after checking the target marking and the HEX memory map. A green/recognized model is not proof that raw silicon ID bits were measured; the current host interface does not expose raw ID/config values to the GUI.
3. The host output and a read-back comparison are shown when available. These paths have not yet been verified on a real programmer, so do not treat a passing software test as hardware acceptance.

The app must not be considered production-ready until Windows and physical-device acceptance testing is complete.

## 4. Other operations (Programmer menu)

* **Erase Only…**, **Verify vs File**, and **Read Chip** are candidate UI operations. Their behavior has not yet been accepted on physical hardware; do not rely on erase/calibration-preservation guarantees before the hardware validation phase passes.
* **Device / Programmer Info** — selected board and target, port, firmware version, package and memory sizes. The upstream ArdPicProg command-line host does not expose raw ID/config words to the GUI; it validates the selected model when each operation starts.

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
| Detected model differs from selected target | Wrong target selection or ambiguous host output | Stop; recheck package marking and selection. Raw ID values are not shown by the app. |
| Verify failed after write | Unstable VPP, bad chip, wiring | Check 13 V supply/wiring; try another chip |
| Port busy / access denied | Another program using the port | Close MPLAB/QPICkit/Serial Monitor |
| HEX “outside memory map” | HEX from a different MCU | Load the HEX built for your selected target |

## 7. Safety notes

* The 13 V VPP supply must never be plugged into the Arduino power jack.
* Do not touch the ZIF/ICSP contacts while programming.
* The upstream ArdPicProg host sends `PWROFF` during normal shutdown; a force-killed process may bypass orderly shutdown. Hardware safety behavior on errors, cancellation, or power loss has not been validated here.
* The upstream ProgramPic source documents inactivity power-off behavior, but this application has not yet passed a physical test of that safeguard.
