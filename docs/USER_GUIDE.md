# Arduino-PIC Programmer — User Guide

**Made By: Ahmed Emad El-Din Hussein** ·
<https://github.com/Ahmed-Emad-EL-Din>

---

## Status: candidate build, not a validated release

The prior Windows workflow passed, but it predates the new installer packaging; the updated workflow has not yet been run. See the README for the artifact instructions once it succeeds. No validated GitHub Release or physical hardware acceptance is available. Treat these steps as candidate behavior, not proof that programming is ready for use; do not perform destructive programming with an unvalidated build.

## 1. Hardware you need

Follow the reference circuit (official Ho-Ro schematic):
**[https://github.com/Ho-Ro/ArdPicProg/blob/master/ArdPicProg_1_8_horo.png](https://github.com/Ho-Ro/ArdPicProg/blob/master/ArdPicProg_1_8_horo.png)**

* An Arduino (Uno / Nano / Pro Mini / Mega / Leonardo) + USB cable
* The ArdPicProg shield (13 V VPP supply + ZIF socket + ICSP header)
  — or the equivalent wiring:
  * **D2 → VDD**, **D3 → MCLR/VPP**, **D4 → CLK**, **D5 → DATA**
    (ProgramPic v1.8.horo pinout)
  * The official shield's documented **16–20 V** VPP input (red LED = VPP OK). Do not substitute a 24 V source unless the exact hardware documentation permits it.
* The target PIC (e.g. PIC16F84A) in the ZIF socket, pin 1 aligned,
  lever locked
* Jumper **JP3**: position 1-2 for 18-pin chips (PIC16F84A),
  2-3 for 8-pin chips (PIC12F675)

## 2. First-time setup (once)

### Step 1 — Install the Windows candidate
1. After the updated Windows workflow succeeds, open that run from the README's workflow link and download **Arduino-PIC-Programmer-Windows-x64-installer**. Earlier runs may use the old combined artifact name.
2. Extract the artifact ZIP. Verify `Arduino-PIC-Programmer-Setup-x64.exe` against its `.sha256` sidecar before installing.
3. Run Setup. It installs per-user, adds a Start menu shortcut, registers in Windows Installed Apps, and includes an uninstaller. This is still a temporary candidate—not a validated hardware release.
4. SmartScreen can warn on unsigned or not-yet-reputed apps. Do not disable it or bypass it for an unvalidated candidate; see the README's SmartScreen note.

### Step 2 — Install ProgramPic firmware if needed
1. In the **Programmer** card, select the Arduino model and port, then choose **Install Firmware…**.
2. The dialog tells you if firmware upload isn't supported for the selected board. Leonardo/Micro must be flashed using Arduino IDE. For Nano, choose the matching old/new bootloader.
3. Upload replaces the Arduino's current sketch. Keep USB connected and remove/reinstall the reset capacitor as directed by the dialog.

### Step 3 — Connect & verify
1. In the **Programmer** card, select the Arduino port and click **Connect** (or use `Ctrl+P`).
2. A successful handshake shows the firmware version. If the port is busy, close Arduino Serial Monitor/other serial tools, select **Rescan**, and retry.

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
