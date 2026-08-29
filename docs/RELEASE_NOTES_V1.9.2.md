# Super Video Pro 1.9.2

Local release candidate built on 2026-08-27.

## Changes

- Added an optional 0-32 px border to every logo overlay.
- Added independent border color selection; 0 px means no border.
- Applied the same border settings to the live preview, saved projects, and FFmpeg export.
- Kept projects created by earlier versions compatible by defaulting to no border.

## Verification

- `pnpm verify`: passed (33 suites, 133 tests), including TypeScript checks and production build.
- Electron playback smoke: passed with a 12 px magenta border; the editor UI and timeline remained mounted after Play.
- Packaged application remained running throughout the 4-second startup smoke window.
- Installer: `release/Super Video Pro Setup 1.9.2.exe` (272,225,300 bytes).
- SHA-256: `35350466A62C1A765FD8B2EA6FD7E5B7CBFACDB4EF4DF878F16E1CC7CBC05850`.
- Authenticode: not signed.
