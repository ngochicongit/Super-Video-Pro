# Super Video Pro 1.9.3

Local release candidate built on 2026-08-27.

## Changes

- Stabilized continuous logo hue, size, and opacity dragging by grouping each pointer gesture into one undo checkpoint.
- Replaced the native video-only fullscreen control with a composed-preview fullscreen control, preserving logo overlays.
- Added explicit fullscreen styling for the video and overlay canvas.

## Verification

- `pnpm verify`: passed (33 suites, 134 tests), including TypeScript checks and production build.
- Packaged application remained running throughout the 4-second startup smoke window.
- Installer: `release/Super Video Pro Setup 1.9.3.exe` (272,224,400 bytes).
- SHA-256: `1B119D3542BDAB43D46F15B972DA0E70D87F88EF0B4DBDE6141CDCC5336FF334`.
- Authenticode: not signed.
