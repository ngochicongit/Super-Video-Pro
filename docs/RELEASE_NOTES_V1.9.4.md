# Super Video Pro 1.9.4

Local release candidate built on 2026-08-27.

## Changes

- Enabled export when a project contains video and logos but no separate audio track.
- Made composition audio optional across the renderer, IPC contract, job manager, and FFmpeg command builder.
- Video-only exports explicitly omit audio while preserving logo, trim, speed, and effect rendering.

## Verification

- `pnpm verify`: passed (34 suites, 138 tests), including TypeScript checks and production build.
- Real FFmpeg integration: passed for a video + logo project without audio.
- Packaged application remained running throughout the 4-second startup smoke window.
- Installer: `release/Super Video Pro Setup 1.9.4.exe` (272,224,407 bytes).
- SHA-256: `251855439CB1AA20E604BADF1B294A8CFA658BAEE117789ADF973535C6B278A4`.
- Authenticode: not signed.
