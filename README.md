# Arduino-PIC Programmer

A Windows desktop workbench for an Arduino-based PIC programmer using the bundled ProgramPic firmware and ArdPicProg host. Load and inspect Intel HEX files, connect to the programmer, select a supported PIC, and run guarded read, erase, program, and verify operations from one Qt application. This project talks to its own Arduino/ProgramPic programmer—not a Microchip PICkit device.

> **Hardware caution:** This project has not completed physical hardware acceptance. A successful build or Windows installer test does not verify electrical safety, target compatibility, VPP voltage, or programming reliability. Treat releases as software candidates; independently validate the exact programmer, target package, datasheet, and wiring before connecting hardware. Do not perform destructive programming based only on the app's checks or the reference drawing.

## Download for Windows

**Latest Windows x64 installer:** [GitHub Releases](https://github.com/Ahmed-Emad-EL-Din/Arduino-PIC-Programmer/releases/latest)

Download `Arduino-PIC-Programmer-Setup-x64.exe` and its `.sha256` sidecar. Verify the checksum before running Setup:

```powershell
$setup = '.\Arduino-PIC-Programmer-Setup-x64.exe'
$sidecar = Get-Content ($setup + '.sha256') -Raw
$expected = ($sidecar.Trim() -split '\s+')[0].ToLowerInvariant()
$actual = (Get-FileHash -Path $setup -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw 'SHA-256 mismatch; do not install this file.' }
```

Setup is a per-user installation and does not require administrator rights. It adds a Start menu shortcut, appears in Windows Installed Apps, and includes an uninstaller; a desktop shortcut is optional. The separate `Arduino-PIC-Programmer-Installer-Windows-x64.zip` contains the installer only—it is **not** a portable application. Extract it and run Setup. Each download has a separate SHA-256 sidecar.

Tagged Windows builds run the test suite, compile the firmware, build the app, validate the package, and smoke-test installation, launch, and uninstall. These are software/CI checks, not physical-device tests. Installers may be unsigned if no trusted Authenticode certificate is configured, so Microsoft Defender SmartScreen may show a publisher or reputation warning. Do not bypass a warning without verifying the source and checksum.

## What it does

- Manages the Arduino serial connection and bundled ProgramPic firmware. Firmware upload uses the Arduino bootloader (Nano: try 115200 baud first, then 57600 if synchronization fails); after flashing, the ProgramPic runtime link uses 9600 baud.
- Opens, inspects, and exports Intel HEX data, with target-memory checks and read-back verification.
- Supports guarded connect, detect, program, erase, read, and verify workflows, with a preflight checklist and confirmation for destructive operations.
- Provides a board/PIC connection table, HEX memory inspector, activity log, themes, and editable firmware source.
- Displays the supplied circuit image in the **Circuit Reference** view. Its board/PIC firmware table is separate from the drawing and is not an electrical validation of it.

See the [User Guide](docs/USER_GUIDE.md) for the application workflow and board-specific notes.

## Hardware, wiring, and VPP safety

Use only a programmer circuit and supply that are documented for your exact hardware revision. Confirm every connection against the board documentation and the target PIC datasheet before applying power.

The bundled ProgramPic firmware communicates with the app at **9600 baud**. This is separate from Arduino bootloader upload speed. The Nano hardware profile uses D2 for switched target VDD, A1 as a **low-voltage VPP-switch control**, D4 for PGC/clock, D7 for bidirectional PGD/data, and A5 for the activity LED. A1 does not generate or tolerate programming voltage: **never connect VPP directly to A1 or any Arduino GPIO**. The external switching circuit must route VPP to MCLR/VPP. Join grounds as required by the verified hardware and place the target's required decoupling capacitor (typically 100 nF) between VDD and VSS.

The [user-supplied circuit image](assets/reference/circuit-reference.png) is an **unverified reference**, not a validated schematic or wiring instruction. It depicts a 24 V DC input and an LM317 regulator; it may not match the firmware pin map or the actual programmer. The project guide describes a 16–20 V input for the official shield—do not apply the image's 24 V input to that shield unless its own documentation explicitly permits it. Do not wire or power hardware from the image or app connection table alone. Verify the specific VPP circuit, voltage, polarity, and target limits independently.

The application does not measure socket voltage. The upstream host does not expose raw silicon ID/configuration values to the UI, and a manual selection cannot electronically identify devices that have no silicon ID. A green connection state or successful software check is not proof that the target wiring or voltage is safe.

## Quick start

1. Install the Windows x64 app from the [latest release](https://github.com/Ahmed-Emad-EL-Din/Arduino-PIC-Programmer/releases/latest) and verify its SHA-256 sidecar.
2. Connect a supported Arduino board by USB. Select its board type and serial port.
3. Use **Programmer → Install/Update ProgramPic Firmware…** to install the bundled firmware. It uses a 9600-baud runtime link; previously installed builds using a different speed must be reflashed before connecting. Leonardo/Micro firmware upload from this app is unsupported; use Arduino IDE for those boards.
4. Select the exact PIC model and load its `.hex` file. Check the package, pinout, supply, and VPP circuit against their documentation.
5. Connect to the programmer at 9600 baud, run the available detection/checks, and complete the on-screen preflight. Review the exact operation before confirming. Back up data first when possible.

For detailed operating instructions, safety notes, and target-specific guidance, read the [User Guide](docs/USER_GUIDE.md). The app's preflight and confirmations are safeguards, not substitutes for hardware validation.

## Supported boards and PIC targets

The firmware profiles include Arduino Uno, Nano (new and old bootloader), 5 V / 16 MHz Pro Mini, Mega 2560, Leonardo, and Micro. The 3.3 V Pro Mini is not electrically compatible with this profile. Firmware upload through the app is unsupported for Leonardo/Micro; use Arduino IDE for those boards.

The current device database includes 25 PIC targets:

`PIC12F629`, `PIC12F675`, `PIC12F683`, `PIC16F630`, `PIC16F676`, `PIC16F84`, `PIC16F84A`, `PIC16F87`, `PIC16F88`, `PIC16F627`, `PIC16F627A`, `PIC16F628`, `PIC16F628A`, `PIC16F648A`, `PIC16F684`, `PIC16F688`, `PIC16F690`, `PIC16F872`, `PIC16F877`, `PIC16F877A`, `PIC16F882`, `PIC16F883`, `PIC16F884`, `PIC16F886`, and `PIC16F887`.

Confirm the exact part number, package, pinout, memory regions, and programmer support before using a target. Similar device names do not guarantee interchangeable wiring or programming requirements.

## Build and test from source

The desktop application uses Python 3.11+, PySide6, and pyserial. In a virtual environment:

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = 'src;.'
python -m pytest -q
```

The Windows release workflow performs the full Windows GUI, package, and installer checks. Its CI results do not replace testing on the exact hardware. Build scripts and packaging configuration are in `packaging/`; the bundled Arduino sketch is in `firmware/source/`.

## Project and licensing

- `src/` — desktop app, programmer protocol, safety checks, HEX handling, and tests.
- `firmware/` — ProgramPic Arduino source and precompiled board images.
- `assets/` — application icons and the supplied circuit-reference image.
- `packaging/` — Windows build and installer configuration.
- `docs/USER_GUIDE.md` — user-facing operating and hardware notes.
- `vendor/ArdPicProg/` — upstream host implementation and attribution.

See [`LICENSE`](LICENSE), [`LGPL-3.0.txt`](LGPL-3.0.txt), and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for project and third-party license information.

**Author:** Ahmed Emad El-Din Hussein · [GitHub](https://github.com/Ahmed-Emad-EL-Din)
