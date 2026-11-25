# Windows Desktop EXE — Completion Plan

This checklist is the source of truth for making a complete, safe, reproducible Windows desktop release. **Do not mark work complete until its acceptance checks have actually passed.** Update the relevant checkboxes when each task ends.

## Current status and scope

- The target is a Windows 10/11 x64 desktop application that a user can download, extract/install, and launch by double-clicking, without installing Python or manually obtaining application dependencies.
- A genuine GitHub Release asset must be attached to a published release. A tag, source archive, or temporary Actions artifact alone does not count as a downloadable release.
- The current checkout is incomplete and cannot produce that application. Do not create or publish a placeholder executable.
- Preserve hardware-safety behavior: no build/release step may weaken device identification, preflight confirmation, verify-after-write, error handling, or safe power-off.

## Phase 0 — Baseline audit (completed)

- [x] Inspect tracked files, branch contents, packaging specification, README, and user guide.
- [x] Check GitHub branches/tags/releases for a complete source tree and existing Windows assets.
- [x] Confirm the `v0.1.0` GitHub Release has no downloadable assets; no Windows `.exe` is currently available.
- [x] Confirm the checkout has no `.github/workflows`, `src/main.py`, `firmware/`, or `assets/` directory.
- [x] Confirm the current PyInstaller spec expects missing entry-point and data files, and the GUI imports modules absent from this checkout.
- [x] Record verification that is possible now: Python syntax compilation and MCU-database smoke checks pass; GUI tests cannot start because PySide6 and required project modules are missing.

## Phase 1 — Restore a complete, trusted source tree (BLOCKING)

- [ ] Locate and restore the complete, known-good application source. Prefer a verified upstream commit or supplied project backup; do not reconstruct hardware-programming logic from guesses.
- [ ] Restore the application entry point, `src/main.py`, and required package initializers.
- [ ] Restore all imported application modules, including at minimum:
  - [ ] `app` metadata/settings and persistent settings implementation.
  - [ ] Core Intel HEX parsing, serial transport, protocol, programmer/session, board pinout, circuit drawing, and `avrdude` integration modules.
  - [ ] GUI theme/icons, worker/task lane, and all dialogs used by the main window (preflight, firmware flash, settings, about).
- [ ] Restore and verify firmware source and/or licensed precompiled firmware for supported Arduino boards.
- [ ] Restore required icons, Qt resources, diagrams, and other runtime assets referenced by the UI/package.
- [ ] Restore a dependency manifest with pinned, compatible versions (PySide6, pyserial, schemdraw, PyInstaller, and test tools as applicable).
- [ ] Restore or establish the correct project license and include all third-party notices/licenses required for redistributed binaries and bundled tools.
- [ ] Add/verify `.gitignore` rules for virtual environments, build output, temporary artifacts, and Python caches.
- [ ] Acceptance: a clean checkout contains every imported module/resource; imports work in a fresh environment; no safety-critical source is silently stubbed or replaced with a dummy implementation.

## Phase 2 — Core behavior and hardware safety

- [ ] Verify the MCU database against the supported firmware/device table: names, IDs/masks, memory regions, config words, EEPROM sizes, and calibration/reserved words.
- [ ] Test Intel HEX parsing for valid records, checksums, EOF, extended addresses, malformed/truncated input, empty files, and address overflow.
- [ ] Test every supported MCU's memory-map validation, HEX-fit rejection, ID match/mismatch, and no-ID behavior.
- [ ] Test serial protocol framing, timeouts, disconnections, malformed replies, and recovery using mocked serial devices.
- [ ] Verify programmer operation order and cancellation/error paths: identify → preflight → erase/write → read-back verify → `PWROFF` safe state.
- [ ] Verify every exit path (success, exception, timeout, cancel, app close) attempts a safe power-off and reports failure clearly if safe state cannot be confirmed.
- [ ] Verify unknown IDs, empty sockets, unsafe voltages, invalid HEX, and mismatched devices block destructive operations.
- [ ] Acceptance: automated safety tests pass; no destructive operation is possible by bypassing a failed safety gate.

## Phase 3 — Desktop application and automated QA

- [ ] Install the pinned dependencies in a clean virtual environment using the documented setup command.
- [ ] Restore/expand unit and integration tests for core logic, GUI startup, menus/dialogs, settings, drag-and-drop HEX loading, logging, and worker cancellation.
- [ ] Use fake serial ports and mocked subprocesses for automated tests; tests must not require a connected Arduino or PIC.
- [ ] Run the full test suite in headless/offscreen mode and resolve all failures.
- [ ] Verify startup with no serial device connected, with no settings file, and with corrupted settings; app must show actionable errors and remain usable.
- [ ] Test supported display scaling and common Windows resolutions; check dialogs, buttons, text, and file paths are not clipped.
- [ ] Acceptance: all automated tests pass from a clean environment; desktop GUI launches without a console window and without hardware attached.

## Phase 4 — Reproducible Windows packaging

- [ ] Repair the PyInstaller spec so its entry point, package discovery, hidden imports, Qt plugins, firmware, icons, and data files exactly match the restored source tree.
- [ ] Decide and document the distribution format based on real Windows testing:
  - [ ] Preferred: a portable package with a clearly visible `Arduino-PIC-Programmer.exe` plus all required runtime files, if that is the reliable Qt/PyInstaller layout.
  - [ ] Use a single-file executable only if firmware, `avrdude`, Qt plugins, and writable runtime data work correctly when extracted/launched from arbitrary paths.
- [ ] Bundle a compatible `avrdude` build and required firmware for each supported board; resolve paths relative to the installed/extracted app, never the developer's checkout.
- [ ] Ensure user settings/logs go to an appropriate writable user-data location, not inside a protected install directory or the temporary one-file extraction folder.
- [ ] Build on a clean Windows x64 GitHub Actions runner; do not claim a Windows executable was validated based only on a Linux build.
- [ ] Make builds reproducible from a tagged source revision and record Python/PyInstaller/dependency versions.
- [ ] Acceptance: the produced package contains all required files, starts on a clean Windows 10/11 x64 machine with no Python installed, and reports missing hardware/COM ports gracefully.

## Phase 5 — Windows and hardware acceptance testing

- [ ] Download the candidate package from a clean Windows test machine and verify its SHA-256 checksum.
- [ ] Extract/install to a path containing spaces and non-ASCII characters; launch the executable by double-clicking and from a normal user account.
- [ ] Verify first-run behavior, settings persistence, file-open/save dialogs, logs, and application shutdown.
- [ ] Verify firmware flashing for each board variant claimed as supported, using the bundled `avrdude`; confirm helpful errors for unavailable ports and unsupported board settings.
- [ ] Bench-test with known-good supported hardware and a current-limited supply before any destructive operation.
- [ ] Test at minimum one supported no-ID PIC and one ID-bearing PIC; verify detection, read, erase/write/verify, and safe power-off against known test HEX files.
- [ ] Test deliberate wrong-device, empty-socket, missing-VPP, serial-disconnect, and verify-failure cases; confirm destructive actions are blocked or safely stopped.
- [ ] Have a second tester follow the user guide from a clean setup and record any ambiguity or mismatch.
- [ ] Acceptance: all tested workflows and failure cases behave as documented; no unresolved high-severity safety, data-loss, or startup bugs remain.

## Phase 6 — Release publication and truthful download link

- [ ] Add a Windows release workflow that builds and tests on tags (for example `vX.Y.Z`) and uploads the final distributable as a release asset.
- [ ] Ensure the workflow fails rather than publishing if tests/build/package validation fail or expected files are absent.
- [ ] Publish the actual `.exe` or portable `.zip` asset to a non-draft GitHub Release; confirm the asset appears in the release API and downloads successfully without authentication.
- [ ] Generate and publish SHA-256 checksums, release notes, supported OS/architecture, install/launch steps, and known limitations.
- [ ] Update `README.md` and `docs/USER_GUIDE.md` with a direct URL to the exact uploaded asset; click-test that URL in a signed-out browser.
- [ ] Remove any claim that the release is ready until the asset and Windows acceptance tests are complete.
- [ ] Acceptance: a new user can download, verify, extract/install, and launch the actual application from the documented release link; no Python or separate dependency installation is required.

## Current blockers / do not mark complete

- [ ] Restore the missing application source, firmware, and runtime assets (Phase 1).
- [ ] Pass automated core and GUI tests (Phases 2–3).
- [ ] Produce and validate a Windows x64 package on Windows (Phases 4–5).
- [ ] Publish a real release asset and test its direct download link (Phase 6).

Until those tasks are complete, the repository has **no ready-to-use Windows executable**. Keep the README honest and do not publish an empty release or placeholder binary.
