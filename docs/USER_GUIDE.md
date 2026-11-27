# Arduino-PIC Programmer — User Guide

**Made By: Ahmed Emad El-Din Hussein** ·
<https://github.com/Ahmed-Emad-EL-Din>

---

## Status: downloadable software candidate, not hardware-validated

The Windows build compiles the firmware and smoke-tests installation, launch, and uninstall. The installer is published on the GitHub Releases page, but no physical Arduino/PIC hardware acceptance or clean-machine validation has been completed. Treat this as a software candidate, not proof that programming is ready for use; do not perform destructive programming with an unvalidated build.

## 1. Hardware you need

The firmware uploaded by this app uses the following Arduino Nano wiring. The upstream Ho-Ro schematic and photographs below may show a different pinout and polarity; treat them as historical references only, not instructions for this firmware.

| Arduino Nano pin | Firmware signal | PIC16F84A connection | Function / notes |
|---|---|---|---|
| A1 | `PIN_MCLR` | Pin 4, MCLR/VPP, through the external VPP switching circuit | HIGH = reset / VPP off; LOW = select approximately 13 V VPP. A1 must only drive the low-voltage switch input—never connect the VPP rail directly to an Arduino pin. |
| D2 | `PIN_VDD` | Pin 14, VDD | HIGH = target 5 V on; LOW = off. Fit 100 nF between PIC VDD and VSS near the device. |
| D4 | `PIN_CLOCK` | Pin 12, RB6/PGC | ICSP clock. |
| D7 | `PIN_DATA` | Pin 13, RB7/PGD | Bidirectional ICSP data. |
| A5 | `PIN_ACTIVITY` | Activity LED anode through a current-limiting resistor; cathode to GND | Indicates serial-command and read/write activity. |
| GND | Common ground | Pin 5, VSS | Join Arduino, PIC, and VPP/VDD circuit grounds. |

Use an Arduino (Nano / Uno / Pro Mini / Mega / Leonardo) and a PIC target. The pin assignments above are the firmware profile; check the exact board pin aliases and PIC package datasheet before wiring. The VPP switching circuit—not A1 itself—must route the external programming voltage to MCLR/VPP. Keep the PIC's documented VPP input isolated from Arduino GPIO and verify supply polarity/voltage before attaching a device.

The app displays the user-supplied PNG circuit image in the single Circuit Reference view, with a board/PIC-specific firmware connection table below it. The drawing is an unverified reference (it depicts a 24 V supply and LM317 regulator) and may not match that table or safe VPP requirements. Check the exact datasheet and hardware guide before wiring; independently verify VPP before connecting a target. Zoom using the controls or Ctrl+mouse wheel; the original PNG can be opened from the same view.

For a PIC16F84A in the published ZIF shield, JP3 is commonly set to 1-2; an 8-pin PIC such as PIC12F675 may require JP3=2-3. Confirm the exact board schematic before selecting jumper positions.

## 2. First-time setup (once)

### Step 1 — Install the Windows candidate
1. Open the project's [GitHub Releases page](https://github.com/Ahmed-Emad-EL-Din/Arduino-PIC-Programmer/releases) and download the latest Windows installer or installer-only ZIP, plus its `.sha256` sidecar.
2. Verify `Arduino-PIC-Programmer-Setup-x64.exe` against its checksum before installing.
3. Run Setup. It installs per-user, adds a Start menu shortcut, registers in Windows Installed Apps, and includes an uninstaller. The release remains a software candidate—not a hardware-validated release.
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
  (dark/light/high contrast, font size), Safety (confirmations, auto-verify)
* **View** — Show Log (`Ctrl+L`), Zoom In/Out (`Ctrl +/-`), Reset,
  Toggle Theme (`Ctrl+T`)
* **Help** — User Guide, Wiring Diagram, ProgramPic Firmware Help,
  QPICkit, Check for Updates, About

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| No ProgramPic response | Firmware missing, wrong port, or port busy | Install ProgramPic and reconnect at 115200 baud. Close other serial apps; rescan if the port is missing. |
| “No response from the Arduino” | Wrong port / firmware missing / Serial Monitor open | Rescan ports, flash firmware, close Serial Monitor |
| “avrdude failed — not in sync” | Wrong board variant or port | Try Nano *Old Bootloader*; press reset and retry |
| `DEVICE failed` | Empty socket, VPP off, chip backwards | Check red VPP LED, pin-1 orientation, lever |
| Detected model differs from selected target | Wrong target selection or ambiguous host output | Stop; recheck package marking and selection. Raw ID values are not shown by the app. |
| Verify failed after write | Unstable VPP, bad chip, wiring | Check 13 V supply/wiring; try another chip |
| Port busy / access denied | Another program using the port | Close MPLAB/QPICkit/Serial Monitor |
| HEX “outside memory map” | HEX from a different MCU | Load the HEX built for your selected target |

The ProgramPic-to-app link and Nano upload both try 115200 baud first. Nano upload retries at 57600 if synchronization fails. If upload fails, check the selected port and close other serial apps.

For an unexpected operation error, use **Copy details** in the error dialog and share that text along with the exported Activity Log. The full rotating diagnostic log is saved at the path shown in the error dialog (up to 2 MB per file, with three backups). If a hardware operation is active when you close the app, the app requests cancellation and stays open until the serial host exits safely; do not force-terminate it while it is writing to a PIC.

## 7. Safety notes

* The 13 V VPP supply must never be plugged into the Arduino power jack.
* Do not touch the ZIF/ICSP contacts while programming.
* The upstream ArdPicProg host sends `PWROFF` during normal shutdown; a force-killed process may bypass orderly shutdown. Hardware safety behavior on errors, cancellation, or power loss has not been validated here.
* The upstream ProgramPic source documents inactivity power-off behavior, but this application has not yet passed a physical test of that safeguard.
