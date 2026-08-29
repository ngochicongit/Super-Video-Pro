# Super Video Pro 1.8.1

## Timeline and overlay UX

- Constrains dragged and exported logos to the visible video frame.
- Makes live logo animation duration react to horizontal and vertical speed settings.
- Adds timeline-local zoom out, zoom slider, zoom in and fit controls.
- Prevents clip selection from starting a reorder gesture; reordering now requires the dedicated `⠿` handle.
- Prevents clicks on clips and track headers from bubbling into timeline seek.
- Keeps animation paths inside the preview frame for horizontal, vertical and bounce modes.

## Verification

- `pnpm verify`: 32 suites and 122 tests passed.
- Electron composition-tab visual smoke passed with the new timeline controls.
- `release/Super Video Pro Setup 1.8.1.exe` was produced successfully (271,416,344 bytes).
- SHA-256: `8134B1086DD4B0AE948A290CE255A35E119A9B5F168CD9F5238AE44420A649CE`.
- The packaged application remained alive during its smoke window.
- Authenticode status is `NotSigned`.
- Repository reuse decision is documented in `docs/EDITOR_REPOSITORY_RESEARCH.md`.

## Release boundary

This is a local Windows release candidate. No external publication or code-signing is claimed.
