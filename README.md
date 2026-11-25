# Arduino-PIC Programmer

**Professional desktop tool that turns an Arduino into a PIC programmer and
uploads HEX files to PIC16F84A (and 25 other PIC devices) — safely.**

Made By: **Ahmed Emad El-Din Hussein** · <https://github.com/Ahmed-Emad-EL-Din>

![Dark theme](docs/screenshot_dark.png)

---

## What it does

1. **Flash Arduino** — writes the *ProgramPic* (ArdPicProg-compatible, v1.8.horo)
   firmware onto your Arduino (Uno, Nano old/new bootloader, Pro Mini
   16/8 MHz, Mega 2560, Leonardo, Micro) using bundled `avrdude` (Windows EXE).
2. **Connect & verify** — performs the `PROGRAM_PIC_VERSION` handshake.
   *No hardware command is ever sent before this passes.*
3. **Load HEX** — strict Intel-HEX parsing (checksum validation) using the
   exact `hex_byte = flat_word × 2` address convention of the reference
   `ardpicprog` host (program + config + EEPROM).
4. **Detect chip** — reads the device ID from the ZIF socket and **hard-blocks
   programming if it doesn't match the selected MCU**.
5. **Program** — preflight checklist → confirmation → erase → write →
   **mandatory read-back verify** → `PWROFF` (safe state).

## Safety design (no room for hardware-destroying mistakes)

| Gate | Behaviour |
|---|---|
| Programmer verified | Every protocol call requires a successful handshake first |
| Device-ID match | Chip ID must equal the selected MCU (mask `0xFFE0`) or the write is refused |
| Empty socket / no VPP | ID `0x3FFF` or unreadable chip → refused |
| No-ID chips (PIC16F84) | Identity cannot be auto-verified → explicit warnings + forced `SETDEVICE` memory map |
| HEX fit check | HEX must only touch regions that exist on the target |
| Preflight checklist | VPP LED, socket, jumper, voltage — all items must be ticked (cannot be disabled) |
| Confirmations | Erase/program dialogs spell out exactly what happens |
| Verify after write | ON by default; turning it off requires extra confirmation |
| Safe state | `PWROFF` after every operation, on errors, on cancel, and on app close |
| Firmware safety net | ProgramPic auto power-offs after 2 s of host inactivity |

## Supported targets

`PIC16F84A` (default), PIC16F84, PIC16F627/A, PIC16F628/A, PIC16F648A,
PIC16F630, PIC16F676, PIC16F684, PIC16F688, PIC16F690, PIC16F87, PIC16F88,
PIC16F872, PIC16F877/A, PIC16F882–887, PIC12F629, PIC12F675, PIC12F683 —
26 devices total, transcribed from the ProgramPic v1.8.horo device table.

## Requirements

* **Windows 10/11** (EXE build) · Linux · macOS
* An Arduino (Uno/Nano/Mega/Pro Mini/Leonardo) with the
  [ArdPicProg ZIF/ICSP shield circuit](https://rweather.github.io/ardpicprog/pic14_zif_circuit.html)
* `avrdude` (auto-detected: bundled `tools/` → PATH → Arduino IDE)

## Run from source

```bash
pip install -r requirements.txt
python src/main.py
```

## Build the Windows EXE

```bat
:: on Windows (cmd)
packaging\build.bat
```
or use the included GitHub Actions workflow
(`.github/workflows/build-windows.yml`) which produces
`dist/Arduino-PIC-Programmer.exe` on every tag — ready to publish.

See [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for the full workflow and
wiring instructions.

## Project layout

```
├── plain.md                  # task plan (checked off as work completes)
├── src/
│   ├── main.py               # entry point
│   ├── app/                  # metadata + settings
│   ├── core/                 # ihex · mcu_db · protocol · serial_link
│   │                         # avrdude · programmer · safety  (unit-tested)
│   ├── gui/                  # theme (design system) · workers · dialogs
│   └── tests/                # 32 tests incl. simulated ArdPicProg device
├── firmware/
│   ├── source/ProgramPic/    # ProgramPic v1.8.horo sketch (Ho-Ro/ArdPicProg)
│   └── precompiled/          # uno · mega2560 · leonardo hex (arduino-cli)
├── tools/                    # avrdude (auto-downloaded on build)
├── assets/                   # icon.ico / icon.png
├── packaging/                # PyInstaller spec + build scripts
└── docs/                     # user guide + screenshots
```

## Credits

* [Ho-Ro/ArdPicProg](https://github.com/Ho-Ro/ArdPicProg) — ProgramPic
  firmware & device table (GPL-3.0)
* [rweather/ardpicprog](https://github.com/rweather/ardpicprog) — original
  project, protocol, ZIF circuit
* [Ho-Ro/QPICkit](https://github.com/Ho-Ro/QPICkit) — host UX inspiration
* [avrdude](https://github.com/avrdudes/avrdude) — Arduino flashing
* Qt `qt-ui-design` agent skill + UI/UX Pro Max — GUI design guidance

## License

GPL-3.0 — see [LICENSE](LICENSE).

## Disclaimer

High-voltage (≈13 V) programming circuitry is involved. The author assumes
no responsibility for damaged chips, boards, or injury. Always verify
wiring, VPP supply, and device selection before programming.
