# Super Video Pro 1.1.0 — Verification Report

Verification date: 2026-08-24 (Asia/Saigon)

## Automated verification

- `pnpm verify`: PASS.
- TypeScript checks: PASS.
- Vitest: 13 test files, 32 tests passed.
- Production Electron and renderer build: PASS.
- New regression coverage verifies terminal-history deletion with artifact cascade and collision-safe output naming.

## Smoke verification

- Curated real-site MP4 and HLS extraction: PASS (`outputs/runtime/real-site-smoke.json`).
- Packaged Browser Sniffer fixture: PASS (`outputs/runtime/browser-sniffer-smoke-v1.1.json`).
- NSIS clean install to isolated directory: exit code 0.
- Installed app loaded packaged renderer with sandboxed preload/IPC bridge: PASS.
- UI displayed version 1.1.0, queue search/filter/cleanup controls, and all bundled tool badges (`outputs/runtime/v1.1-installed-ui.png`).
- Existing V1 settings were read without migration or data reset, confirming the unchanged V1 persistence contract.
- Safe update check returned `not-configured` because no distributor feed is configured.
- Silent uninstall: exit code 0; isolated installation directory removed.

## Release artifact

- File: `release/Super Video Pro Setup 1.1.0.exe`
- Size: 241,533,127 bytes
- SHA-256: `AE97A5F9B866CDDB57EAF5445796FAD3FE2AA509F8A424F422744ED71F32517F`

## Result

All defined V1.1 hardening gates pass. The release is approved for handoff.
