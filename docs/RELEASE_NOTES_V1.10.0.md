# Super Video Pro 1.10.0

Local release candidate built on 2026-08-28.

## Changes

- Added a persistent local UI refactor workspace with design DNA, viewport configuration, measurements, screenshots, scoring, and HTML reports.
- Added `ui:init`, `ui:audit`, and `ui:verify` commands and repository rules for bounded UI improvements.
- Added keyboard navigation across tabs with Arrow keys, Home, and End using the roving-tabindex pattern.
- Standardized spacing, radius, focus-ring, interaction-target, and reduced-motion tokens without changing the existing navy/teal design language.
- Added deterministic checks for accessible control names, target sizes, page overflow, tab semantics, and renderer failures.

## Verification

- UI audit: 92/100, passing the configured 90-point gate over 6 app states.
- `pnpm verify`: passed (34 suites, 140 tests), including TypeScript checks and production build.
- Packaged application remained running throughout the 4-second startup smoke window.
- Installer: `release/Super Video Pro Setup 1.10.0.exe` (272,226,112 bytes).
- SHA-256: `7613DA1CCC77165E276F915FEE4520C9D1A90E9EF05EC4947C521553E18999A1`.
- Authenticode: not signed.
