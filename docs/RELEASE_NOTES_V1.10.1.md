# Super Video Pro 1.10.1

Local release candidate built on 2026-08-28.

## Changes

- Strengthened editor panel hierarchy while preserving the navy and teal design language.
- Added accented panel headings, clearer selected-media states, and consistent editor scrollbars.
- Increased preview depth and separated transport controls from the canvas.
- Improved timeline track layering, hover feedback, and visual boundaries.

## Verification

- UI audit: 92/100 over 6 app states with no new page overflow or renderer failures.
- Compact and desktop screenshots visually reviewed.
- `pnpm verify`: passed (34 suites, 141 tests), including TypeScript checks and production build.
- Packaged application remained running throughout the 4-second startup smoke window.
- Installer: `release/Super Video Pro Setup 1.10.1.exe` (272,226,646 bytes).
- SHA-256: `258919DE0B5CF46EBA8767BBC0E291119752789FB140B7B5C3DD127820BF3418`.
- Authenticode: not signed.
