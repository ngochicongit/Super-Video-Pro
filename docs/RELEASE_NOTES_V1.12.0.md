# Super Video Pro 1.12.0

Local release candidate built on 2026-08-28.

## Changes

- Reduced the primary workspace navigation to Download, Media editor, and History.
- Replaced the Tasks tab with a global right-side drawer available from every workspace.
- Combined active download and media-composition progress in the Tasks drawer.
- Replaced the Settings tab with a focused, independently scrollable modal panel.
- Added backdrop click, close buttons, Escape handling, modal semantics, and inert background content.
- Extended UI audit automation to open and measure task and settings surfaces directly.
- Isolated Electron audit profiles to prevent Windows cache contention between screenshot runs.
- Replaced the encoding-sensitive empty-state glyph with a CSS-rendered icon.

## Verification

- UI audit: 93/100 over 15 workspace and surface states.
- No renderer failures or page-level horizontal overflow detected.
- Task drawer and Settings modal visually reviewed at compact and desktop sizes.
- `pnpm verify`: passed (34 suites, 142 tests), including TypeScript checks and production build.
- Packaged application remained running throughout the 4-second startup smoke window.
- Installer: `release/Super Video Pro Setup 1.12.0.exe` (272,228,177 bytes).
- SHA-256: `4F216CC0F5D5C0296A8E1280832ED63C450CE0B58DA7E11B86F624C6E84C55B9`.
- Authenticode: not signed.
