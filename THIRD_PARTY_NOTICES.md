# Third-party software and license notices

The portable Windows package includes or is built with third-party components. Their licenses remain applicable; this notice does not replace the license texts delivered with the package.

- **ArdPicProg host and ProgramPic firmware** — Ho-Ro / Southern Storm Software, GPL-3.0. Source is included under `vendor/ArdPicProg/` and `firmware/source/`; see `LICENSE` and `vendor/ArdPicProg/UPSTREAM.md`.
- **PySide6 / Qt 6** — LGPL-3.0-or-later or GPL/commercial terms depending on the component and use. `LGPL-3.0.txt` is included. The package must preserve Qt's notices and allow replacement of the dynamically linked Qt libraries.
- **pyserial** — BSD-3-Clause; project: <https://github.com/pyserial/pyserial>.
- **PyInstaller** — GPL with the PyInstaller bootloader exception; project: <https://github.com/pyinstaller/pyinstaller>.
- **Arduino AVR platform / avrdude** — licenses and source notices are supplied by the Arduino platform packages. The Windows build stages the available avrdude license notice beside the bundled tool where present; release packaging must verify and retain those notices.

Before publishing a binary, inspect the built package and include the licenses/notices shipped by the exact dependency versions. Do not strip third-party copyright notices.
