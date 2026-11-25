# Repair Checklist

Scope is limited to the current Arena branch. The repository's `main` and the
previous Arena branch currently contain the same project snapshot; this session
must not switch branches or push changes directly to `main`.

- [x] Inspect current branch, repository contents, and the previously named branch.
- [x] Check whether the README's claimed Windows release and downloadable asset exist.
- [x] Correct the README download destination and accurately state release availability.
- [x] Remove or correct documentation claims that point to files absent from this checkout.
- [x] Run available static checks and tests; record any blockers caused by missing project files/dependencies.
- [x] Review the final diff and ensure the checklist reflects completed work.

## Verification notes

- GitHub currently reports no releases or release assets for this repository. README now links to the releases page and explicitly states that no executable can currently be downloaded.
- `python -m compileall -q src`: passed.
- MCU database smoke checks: passed (25 entries, lookup, ID matching, no-ID device).
- Markdown local-image check: passed; all referenced local images exist.
- GUI unit tests could not start: `PySide6` is not installed. The checkout also lacks most imported Python modules, the app entry point, firmware, assets, and `.github/workflows`; it cannot be built or run end-to-end from this tree.
