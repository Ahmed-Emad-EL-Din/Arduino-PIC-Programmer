# Windows Desktop EXE — Source, Build, and Release Checklist

This is the execution checklist for producing a complete, safe, reproducible Windows x64 desktop package. **Mark a task `[x]` only after its stated work and checks actually pass.** A successful compile is not the same as a hardware-validated release.

## Active follow-up — Microsoft Windows development skills (PR #28)

### Phase 1 — Skill review and applicability
- [x] Read `microsoft/win-dev-skills` and its pinned `winui` / `winappcli` guidance.
- [x] Select the cross-framework `winapp-ui-automation` skill and transferable design practices for this PySide6 app.
- [x] Keep WinUI-only XAML/API samples and MSIX conversion out of scope; the app is PySide6 and uses an established EXE/installer release path.

### Phase 2 — Focused app improvements
- [x] Add a selectable, high-contrast appearance and carry it through widgets, status log, and generated wiring views.
- [x] Strengthen visible keyboard-focus styling and align shared control spacing to a four-pixel rhythm.
- [x] Give key operation/status controls clear accessible names and preserve existing safety language.
- [x] Add Windows UI Automation coverage using `winapp ui` for the main workbench’s key controls.

### Phase 3 — Verification
- [x] Run pure-Python/theme and non-GUI regression tests plus compile/whitespace checks locally.
- [x] Run full GUI and `winapp ui` checks on Windows CI; record failures/limits rather than marking unverified work complete.
- [x] Review PR checks and update this phase checklist with actual outcomes.

Local results: `PYTHONPATH=.:src .venv/bin/pytest -q src/tests --ignore=src/tests/test_gui.py` passed (42 tests, 29 subtests); `compileall`, workflow YAML parsing, and `git diff --check` passed. Windows run `46047111968` passed the full GUI suite, all `winapp ui` accessible-control searches, package validation, installer smoke test, and checksum/ZIP creation. Earlier runs exposed stale GUI assertions and a PATH precedence issue; both were fixed before this passing run.

## Current follow-up — use the supplied Drive circuit image

### Phase 1 — Image integration
- [x] Download and inspect the provided PNG (3570 × 2978; 1,220,742 bytes).
- [x] Display the supplied PNG directly in the Circuit Reference view with zoom/fit controls; keep the firmware connection table below it as a separate reference.
- [x] Preserve the warning that the unverified drawing depicts a 24 V supply/LM317 regulator and may not match the firmware map or safe VPP requirements.

### Phase 2 — Packaging and docs
- [x] Bundle the PNG in the Windows package and update the package validation list.
- [x] Update README and user guide to identify the supplied image rather than the XML source.
- [x] Remove the unused XML/SVG renderer and diagram source asset.

### Phase 3 — Verification
- [x] Run 18 available pure-Python unit tests; run `compileall`, package-spec syntax/image-path checks, stale-reference checks, and `git diff --check`.
- [ ] Run the PySide6 GUI suite and Windows packaged-app checks; unavailable locally because PySide6 is not installed. Pytest and YAML parsers are also absent in this environment.

## Current follow-up — crop the supplied Drive image for the app icon

### Phase 1 — Source image and crop
- [x] Download and inspect the exact Drive PNG; trim its transparent canvas to the rounded-square artwork without redrawing or changing the design.
- [x] Square-fit the crop while preserving transparency at the rounded corners.

### Phase 2 — App asset integration
- [x] Regenerate `assets/app-icon.png`, its exact-image SVG wrapper, and the multi-resolution Windows ICO from the cropped artwork.
- [x] Preserve existing app/package references to `assets/app-icon.ico`.

### Phase 3 — Validation
- [x] Validate embedded SVG/ICO/PNG agreement and 256/128/64/48/32/16 ICO sizes; pass 20 available unit tests, `compileall`, and `git diff --check`.
- [ ] Run GUI and Windows packaged-app checks; PySide6/pytest are not installed in this environment.

## Goal and release definition

- Deliver a portable Windows 10/11 x64 package that a user can extract and launch by double-clicking `Arduino-PIC-Programmer.exe`, without installing Python or separately downloading runtime dependencies.

## Current guidance and README circuit update

- [x] Shorten the in-app connection and target guidance while retaining actionable next steps and critical limits (target ID and socket voltage are not measured).
- [x] Rename the app's generated "Circuit Schematic" view to "Wiring Overview" and label it illustrative, not an electrical schematic.
- [x] Remove the unsuitable generic supply image and its incorrect resistor/output claims from the README.
- [x] Replace it with a standard LM317 divider reference: R1=120 Ω OUT-to-ADJ, R2=1.12 kΩ ADJ-to-common, 0.1 µF input bypass, 1 µF output capacitor; clearly label ≈13 V as VPP-only and the drawing as unvalidated.
- [x] Clarify that the official shield's stated 16–20 V input must not be confused with this independent 24 V reference circuit.
- [x] Parse the SVG as XML and run diff whitespace checks.
- [x] Render and visually inspect the circuit SVG; verify feedback resistor/capacitor connections and that labels do not overlap.
- [x] Run the Windows GUI/build workflow on this change: PR run `45825021860` passed GUI tests, package inventory checks, and no-hardware packaged startup; it uploaded screenshots plus candidate artifacts.
- [ ] Visually inspect real application screenshots. Download of the latest screenshot artifact from run `45825021860` still ends with EOF; do not claim visual sign-off without opening the actual captures.
- [ ] Bench-validate the supply and programmer hardware before claiming electrical suitability.

- The ZIP/package must include the Qt runtime, ArdPicProg host helper, firmware images, avrdude and its configuration/dependencies/notices, user guide, and required license notices.
- A GitHub tag, source archive, or temporary Actions artifact is **not** a published release. A real `.exe`/`.zip` must be attached to a non-draft GitHub Release and its direct URL tested signed out.
- Keep hardware safeguards. Do not publish a fake/stub executable or claim physical validation before it has been performed.

## Baseline findings (completed)

- [x] Inspect the starting tree, existing GUI, PyInstaller spec, README, tests, branches, tags, and releases.
- [x] Confirm the initial checkout had no app entry point, most imported modules, firmware, runtime assets, or build workflow.
- [x] Confirm GitHub's `v0.1.0` release has no assets and the prior `v2.0.0` asset URL was broken.
- [x] Inspect upstream `Ho-Ro/ArdPicProg`: it contains the GPL-3.0 C++ host and ProgramPic sketch, but not this repository's custom Qt UI.
- [x] Pin the upstream reference source to commit `420aacef1990a1d0ce348a468ff44a73dcb554e3`.

## Phase 1 — Restore the application source tree

- [x] Vendor upstream ArdPicProg host C++ sources, its Windows/POSIX serial backends, upstream notice, and full GPL-3.0 text under `vendor/ArdPicProg/`.
- [x] Restore upstream `ProgramPic.ino` and firmware README under `firmware/source/`.
- [x] Restore `src/main.py`, `app/` metadata/settings, package initializers, and the missing core/GUI modules needed by existing imports.
- [x] Add pinned Python runtime/build/test dependencies in `requirements.txt`.
- [x] Add root GPL-3.0 and LGPL-3.0 license texts plus third-party notices.
- [x] Restore the official ArdPicProg schematic/photo used by the GUI reference tab; SVG icons/diagrams are generated by source.
- [x] Add ignore rules for generated tools, firmware, build output, environments, and Python caches.
- [x] Add a safe Python adapter that uses the upstream host for serial operations, verifies written addresses by read-back, and does not fabricate measured chip IDs from expected database values.
- [x] Add explicit unverified-pinout warnings instead of inventing package pin numbers, and an extra manual-identity warning for no-ID devices.
- [x] Review module imports and Windows GUI startup: full CI suite passed and the packaged app stayed open in the no-hardware smoke test (run `45825021860`). Local GUI imports remain blocked by missing Linux system libraries (`libGL`, `libEGL`, `libxkbcommon`, `libdbus`).
- [ ] Restore/validate exact pin maps for every MCU before describing every target's physical wiring as verified.
- [ ] Acceptance: a clean checkout starts the complete desktop UI; every internal import resolves; no dummy hardware operation or unverified destructive path remains.

## Phase 2 — Core behavior and safety validation

- [x] Implement strict Intel HEX parsing: record lengths, checksums, EOF, supported address ranges, conflicts, and PIC word/EEPROM conversion.
- [x] Add HEX regression tests for PIC memory round-trip, EEPROM conversion, checksum rejection, required EOF, duplicate conflicts, and unpaired bytes.
- [x] Add mock-host tests for connect/detect adapter behavior and read-back mismatch rejection.
- [x] Test raw-ID gate match/mismatch, blank/unavailable IDs, no-ID manual selection, and warnings for unverified package pinouts.
- [x] Generate the schematic and verified/fallback pinout SVGs without an external drawing dependency; XML parse tests pass.
- [ ] Verify the 25-entry MCU database against the exact upstream firmware table, including IDs/masks, memory regions, config/EEPROM sizes, and calibration words.
- [ ] Test the HEX fit gate and device mismatch/no-ID/empty-socket cases for every device family.
- [ ] Test protocol timeouts, serial loss, malformed replies, exit paths, and power-off using a simulator or mock serial endpoint.
- [ ] Verify upstream host behavior for erase, calibration preservation, program, read, and verify against the specific firmware version shipped.
- [ ] Confirm every operation/exception/cancel/close path returns the programmer to safe state. Current cancel behavior deliberately defers until the active host process can close normally; test that behavior.
- [ ] Acceptance: all automated safety tests pass, failed identity/HEX/preflight gates block destructive commands, and post-write comparison is mandatory by default.

## Phase 3 — Desktop UI and automated QA

- [x] Create/restore the app entry point, persistent settings, dialogs, theme, icons, and worker lane required by the workbench.
- [x] Add test coverage for HEX parsing, backend adapter results, SVG validity, and the current contextual-control/disclosure states.
- [x] Add real Qt window screenshot capture for dark/light home screens and the HEX inspector; add an Actions artifact upload step for review.
- [x] Run the screenshot-enabled GUI integration suite on Windows for this change; run `45825021860` passed.
- [x] Generate fresh real-app screenshots for dark/light no-hardware home and the HEX inspector; artifact `Arduino-PIC-Programmer-UI-screenshots` is attached to run `45825021860`.
- [x] Run the new connection/disclosure GUI tests on Windows as part of that suite.
- [ ] Visually inspect the fresh screenshots from run `45825021860` for clipping, readability, spacing, and misleading states. Artifact download still fails with EOF; visual sign-off remains pending.
- [ ] Test startup without hardware, settings file, or recent files; test corrupt settings and unavailable COM ports.
- [ ] Test file open/drag-drop/save, recent files, preflight dismissal/acceptance, settings persistence, cancellation, and clean shutdown.
- [ ] Test the UI at common Windows DPI scales and resolutions; ensure dialogs/buttons/text remain visible.
- [x] Acceptance: Windows CI passes the full automated suite and the packaged GUI stays open in an offscreen no-hardware smoke launch (run `45825021860`). Clean-machine interactive launch is still a Phase 5 requirement.

## Phase 3.5 — Detailed UX improvement and visual acceptance

### UX principles (must hold in every screen and dialog)
- Selected board/target, programmer-reported model, raw measured silicon ID, and physical voltage are distinct concepts. Label each honestly; never make a selected value look detected or measured.
- No UI text may say the socket is at 0 V, unpowered, safe, or physically verified unless hardware actually reports that measurement. The current host does not expose socket voltage or raw ID/config words.
- Every enabled action explains its preconditions; every disabled action has a concise reason. Show one clear next step for no-port, disconnected, no-HEX, unsupported-target, and busy states.
- A green success indicator means a named software postcondition actually passed (for example, HEX read-back comparison); it must not imply physical voltage, wiring, or safety was measured.
- Destructive actions are visually distinct, describe erase/calibration consequences, use a safe default, and require an explicit review/confirmation that names the selected target and file.
- Errors state what failed, what the app did/did not do, what the user should check next, and whether retrying is safe. Avoid raw tracebacks as the only user feedback.
- Keep the visual language restrained and purposeful: strong type hierarchy, consistent spacing, a small semantic color set, and no decorative metrics, oversized labels, stock imagery, or claims that the hardware has been verified.

### UX research references
- [Microsoft desktop UX: designing for simplicity and power](https://learn.microsoft.com/en-us/windows/win32/uxguide/how-to-design-desktop-ux) — keep core tasks obvious, constrain invalid choices, and progressively disclose secondary controls.
- [Microsoft desktop UX checklist](https://learn.microsoft.com/en-us/windows/win32/uxguide/top-violations) — make controls discoverable and errors specific, actionable, and non-blaming.
- [Microsoft accessibility guidance](https://github.com/MicrosoftDocs/win32/blob/docs/desktop-src/uxguide/inter-accessibility.md) — preserve keyboard access and meaningful system accessibility behavior.

### Screen-by-screen review
- [x] Replace unsupported “0 V/safe/powered off” UI claims with explicit “voltage not measured” guidance; distinguish selected target from the programmer's reported model and explain the host's raw-ID limitation.
- [x] Make programming summaries reflect the actual read-back and calibration-preservation settings; block erase when calibration preservation is unchecked and no explicit calibration backup is supplied. Core regression tests pass.
- [x] Rerun the Windows GUI tests after the copy/confirmation changes; the first run exposed a missing HEX-warning caveat, which was fixed. Updated Windows run `45761718540` passes.
- [ ] Visually inspect the fresh screenshots from passing run `45825021860`; the signed screenshot download still returns EOF.
- [x] First launch: the numbered board/port → target → HEX flow is visible; no-port guidance gives the next step, and the user guide is reachable from Help.
- [x] Board and port card: board selection is labeled as a wiring reference, missing ports point to Rescan, busy serial-port errors give recovery steps, and Leonardo/Micro firmware upload limits are shown before flashing. Windows GUI regression tests cover the upload limitation and port-error guidance.
- [x] Ease-of-use pass: Connect stays disabled until a port is selected, Connect/Disconnect swap in place, and optional Blank Check/Read Backup/Erase tools are collapsed behind “More target actions.” The Windows GUI tests for these states pass in run `45825021860`.
- [x] Programmer connection: show the selected port and handshake-reported firmware separately from target identity; show connect/disconnect state and a persistent next-step hint.
- [x] Target card: label the MCU as selected, separate ProgramPic's reported model, disclose raw-ID limitations, and warn for no-ID/manual marking or unverified wiring. A reported-model mismatch now blocks hardware actions until resolved.
- [x] HEX card: show filename and region counts; identify fit/mismatch inline, block Program/Verify for out-of-range images, and explain that a memory-map fit does not verify hardware identity or wiring.
- [x] Circuit/pinout inspector: show selected board/target and jumper mode; retain explicit unverified mapping and datasheet guidance.
- [x] Preflight and confirmation dialogs: use a checklist, describe operation consequences, and make Cancel the default/focused response.
- [x] Progress/cancel: identify the active operation and retain deferred-cancel wording; progress is shown only when the host reports it.
- [x] Success/failure: separate write completion from read-back comparison, disclose when comparison is disabled, and state that socket voltage is not measured.
- [ ] Activity log: timestamps, severity, copy/export/filter are implemented; review duplicate volume and error recovery UX.
- [ ] Settings/About/Help: links/version and settings are present; review explanations for baud, verification, calibration preservation, and known limitations.

### Accessibility, consistency, and responsive layout
- [ ] Check keyboard-only operation: logical Tab order, visible focus, Enter/Escape behavior, useful shortcuts, and no keyboard traps in dialogs/tabs.
- [ ] Give controls accessible names and meaningful tooltips; do not rely on color alone for status or severity.
- [ ] Check text contrast in dark and light themes, minimum readable font sizes, high-DPI scaling, and no clipped controls at 100%, 150%, and 200% Windows scaling.
- [ ] Check minimum-size and resized layouts with the activity log both shown and hidden; controls and status must remain reachable without horizontal scrolling.
- [ ] Standardize terminology, button verbs, status colors/icons, spacing, and dialog button order; remove jargon or define it at first use.

### Real-image review / visual regression
- [x] Capture real Qt app windows (not mockups): dark no-hardware home, light no-hardware home, and dark HEX inspector. Fresh screenshots are in the [passing Actions run](https://github.com/Ahmed-Emad-EL-Din/Arduino-PIC-Programmer/actions/runs/45819350412), artifact `Arduino-PIC-Programmer-UI-screenshots`.
- [ ] Download and inspect the fresh Windows captures at 100% and enlarged. `gh run download` currently receives EOF from the signed artifact host.
- [ ] Keep screenshots as a short-lived CI artifact unless approved documentation images are deliberately curated; don't commit raw build/test output accidentally.
- [ ] Acceptance: a first-time user can identify the next safe step, understand what the app knows versus what it cannot measure, and recover from common errors without guessing.

## Phase 4 — Firmware and Windows packaging

- [x] Repair the PyInstaller spec to point to the actual repository root and include optional runtime folders/licenses.
- [x] Add `packaging/build_host_windows.sh` to build/smoke-test the bundled Windows ArdPicProg host helper under MSYS2.
- [x] Add `packaging/build_firmware.ps1` to compile board-specific ProgramPic images and stage avrdude/configuration for packaging.
- [x] Add a Windows GitHub Actions candidate-build workflow that compiles, tests, packages, checks required files, and uploads a short-lived candidate artifact.
- [x] Build the upstream ArdPicProg POSIX host locally and confirm its CLI help starts; this is only a source smoke test, not a Windows build.
- [x] Run the Windows workflow for commit `f7638bed1f681e50c47502de97f4911dfcfe6f51`; it completed successfully with passing tests, firmware compilation, packaging, required-file checks, screenshots, test report, and generated/validated ZIP checksum (Actions run `45761718540`).
- [x] Produce the portable onedir candidate artifact with `Arduino-PIC-Programmer.exe` at the package root; CI confirmed the executable and core bundled host/avrdude/firmware files exist. Clean-machine launch remains unverified (Phase 5).
- [x] Verify `ardpicprog.exe`, avrdude/config and adjacent DLLs, all seven firmware images, the Qt Windows platform plugin, user guide, reference schematic, and required notices exist in the built package (run `45825021860`).
- [ ] Verify bootloader handling for Uno/Nano/Mega/5V Pro Mini. Leonardo/Micro flashing through this dialog is explicitly unsupported until their bootloader port-reset flow is implemented; do not claim those upload paths work.
- [ ] Acceptance: candidate package launches on a clean Windows 10/11 x64 machine, every required input is present, and missing ports/files produce actionable errors.

## Phase 5 — Windows and hardware acceptance

- [ ] Download the candidate artifact on a clean Windows system and verify its published SHA-256.
- [ ] Extract to a path with spaces/non-ASCII characters and launch as a normal user by double-clicking the EXE.
- [ ] Verify settings/log locations are writable and survive restart; verify the app closes without orphaned host processes.
- [ ] Flash ProgramPic to each board variant claimed as supported, or document the required Arduino IDE procedure where GUI flashing is unsupported.
- [ ] Bench-test with a current-limited supply and known-good programmer hardware before destructive tests.
- [ ] Test at least PIC16F84A and PIC12F675 detection/read/erase/program/read-back verification/power-off with known HEX.
- [ ] Test wrong target, unknown ID, no-ID target selection, empty socket, missing VPP, serial disconnect, cancel, and verify failure; confirm writes are blocked or report failure safely.
- [ ] Have a second tester follow the guide from a clean setup and capture any mismatches.
- [ ] Acceptance: all claimed workflows and failure cases are physically verified; no unresolved high-severity safety, data-loss, or launch issue remains.

## Phase 5.5 — Product trust, support, and final QA

- [ ] Review actual UI screenshots from the latest passing Windows run `45825021860` (artifact download currently ends with EOF); review clipping, spacing, text legibility, and hardware-state claims.
- [ ] Verify empty/no-hardware, disconnected, loading, failure, success, and destructive-confirmation UI states; ensure errors are actionable and success is never reported prematurely.
- [ ] Review keyboard navigation, accessible names/focus order, high-DPI scaling, minimum window size, and common 100%/150%/200% Windows display scales.
- [ ] Verify app branding: final product name/version, executable metadata/icon, support URL, About dialog, and no development suffix in a release build.
- [x] Generate and CI-validate a `.sha256` sidecar for every candidate ZIP (verified in run `45729144989`).
- [ ] Independently verify the downloaded candidate checksum on a clean Windows PC and publish checksum next to final release assets.
- [ ] Produce a dependency/license inventory (SBOM or equivalent), confirm all bundled notices/licenses are included, and document known limits and supported board/PIC combinations.
- [x] Upgrade checkout, setup-python, and artifact-upload actions to current Node 24-compatible major releases; the latest workflow passed without check-run warnings.
- [ ] Pin third-party GitHub Actions to immutable commit SHAs and add a routine dependency/security update process before public releases.
- [ ] Decide and document Windows code-signing policy. If unsigned, clearly state SmartScreen may warn; never imply an unsigned build is signed/trusted.
- [ ] Confirm portable settings/log locations, data retention, privacy behavior, and clean uninstall/removal instructions.
- [ ] Acceptance: a new tester can find the download, understand the candidate/release status and risks, launch it, diagnose common errors, and verify the package/checksum without relying on chat support.

## Phase 6 — Publish the real release

- [ ] Do not publish a release until Phases 2–5 acceptance criteria pass.
- [ ] Create a version tag from the validated source commit and run the Windows build workflow on that exact tag.
- [ ] Attach the installer-only ZIP (containing only the setup EXE) to a non-draft GitHub Release; include its SHA-256, OS/architecture, setup steps, supported boards/targets, and limitations.
- [ ] Verify the asset appears in GitHub Release metadata and can be downloaded without authentication.
- [ ] Update README and user guide with the exact asset download URL; click-test it signed out and confirm the downloaded package launches.
- [ ] Acceptance: a new user can download, verify, extract, and run the genuine application directly from the release package without installing Python or separate runtime tools.

## Verification run so far

- `python -m compileall -q src app`: passed after the current ease-of-use changes.
- `PYTHONPATH=src .venv/bin/python -m pytest -q src/tests/test_ihex.py src/tests/test_programmer_adapter.py src/tests/test_svg.py src/tests/test_safety.py`: **18 passed** locally.
- Current GUI integration tests cannot run in this Linux sandbox: PySide6 imports fail because system `libGL.so.1` is absent. Windows run `45825021860` passed the screenshot-enabled GUI suite, including no-port Connect gating, contextual Connect/Disconnect controls, advanced-action disclosure, unsupported-board firmware guidance, and port-error recovery hints.
- `bash packaging/build_host_posix.sh`: built the upstream C++ helper into ignored `tools/ardpicprog`; CLI help smoke test passed.
- `git diff --check`: passed on the current changes.
- PyInstaller spec path was corrected after an initial failed attempt. A Linux packaging attempt is still blocked because the sandbox Python lacks `libpython3.11.so.1.0`; this is not a Windows build result.
- Windows CI passed at PR head `23044ba` in run `45825021860`; it produced a candidate ZIP, SHA-256 sidecar, test report, and fresh UI screenshots. Package inventory checks and a no-hardware packaged-app launch smoke test passed. These are temporary Actions artifacts, not a published Release. The screenshots remain unreviewed because artifact downloads end with EOF. No clean-machine Windows launch or physical hardware test has been performed.

## Remaining release blockers

- [x] Run the Windows build/test workflow after inline-guidance, mismatch-gating, theme, and ease-of-use changes (run `45819350412`).
- [ ] Physically validate the adapter and safety behavior with supported hardware.
- [ ] Publish and test a real GitHub Release asset.

Until every blocker above is checked, describe this as a **candidate source/build pipeline**, not a ready-to-use released EXE.
