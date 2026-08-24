# Super Video Pro 1.2.0 — Verification Report

Verification date: 2026-08-24 (Asia/Saigon)

## Automated verification

- `pnpm verify`: PASS.
- TypeScript: PASS.
- Vitest: 13 files, 34 tests passed.
- Renderer/Electron production build: PASS.
- Non-locale source scan: PASS; non-ASCII text exists only in the dedicated Vietnamese locale file.
- Window-control and structured debug-log IPC schemas are covered by contract tests.

## Packaged UI and download proof

- Final NSIS installer clean-installed with exit code 0.
- Packaged application loaded from `app.asar` with sandboxed preload/IPC.
- Native Windows title bar was absent; custom draggable title bar, traffic-light controls, branded icon and version 1.2.0 rendered successfully.
- The packaged renderer inspected `https://www.w3schools.com/html/mov_bbb.mp4`, displayed the explicit **Tải xuống** action, created a queue job, downloaded 788,493 bytes, validated the output and reached `completed`.
- Evidence: `outputs/runtime/v1.2-final-installed-ui.png`, `outputs/runtime/v1.2-final-installed-ui.png.json`, and `outputs/runtime/v1.2-final-download/mov_bbb.mp4`.
- Local diagnostics recorded `ui.action` events and throttled job state/progress entries under Electron `userData/logs/app.jsonl`.
- Silent uninstall returned exit code 0 and removed the isolated installation directory.

## Icon evidence

- Master raster: `assets/super-video-pro-icon-master.png`.
- Runtime PNG: `assets/icon.png`.
- Windows multi-size icon: `assets/icon.ico`.
- Electron Builder packaged without the previous default-icon warning.

## Release artifact

- File: `release/Super Video Pro Setup 1.2.0.exe`
- Size: 242,490,535 bytes
- SHA-256: `BB0E13314BCC15F241F107C4C40ED7A536FEAA65C9FE9C0908B59161F456EE9A`

## Result

All requested V1.2 download, logging, localization, interaction, icon and custom-window requirements pass and the release is approved for handoff.
