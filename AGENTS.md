# Repository guidance

## UI work

Preserve the existing dark navy and teal desktop-editor design language documented in `.ui-refactor/design/DESIGN.md`.

Before changing shared UI, run `pnpm ui:audit` and inspect `.ui-refactor/latest.json`. Prefer one root-cause patch in tokens or shared components over repeated component-level overrides. After a UI patch, run `pnpm ui:verify` and `pnpm verify`.

A UI patch is complete only when the UI score meets the configured target, renderer errors and page-level horizontal overflow do not increase, tab keyboard behavior remains valid, TypeScript passes, and all tests pass. Do not treat intentionally scrollable timeline internals or development-only Electron warnings as page regressions.

Never replace the existing visual language unless the user explicitly requests a redesign. Respect `prefers-reduced-motion`, preserve visible keyboard focus, and keep interactive targets at least 32 px in this compact desktop interface.
