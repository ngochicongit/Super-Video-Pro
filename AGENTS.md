# Repository guidance

## UI work

Preserve the existing dark navy and teal desktop-editor design language documented in `.ui-refactor/design/DESIGN.md`.

Before changing shared UI, run `pnpm ui:audit` and inspect `.ui-refactor/latest.json`. Prefer one root-cause patch in tokens or shared components over repeated component-level overrides. After a UI patch, run `pnpm ui:verify` and `pnpm verify`.

A UI patch is complete only when the UI score meets the configured target, renderer errors and page-level horizontal overflow do not increase, tab keyboard behavior remains valid, TypeScript passes, and all tests pass. Do not treat intentionally scrollable timeline internals or development-only Electron warnings as page regressions.

Never replace the existing visual language unless the user explicitly requests a redesign. Respect `prefers-reduced-motion`, preserve visible keyboard focus, and keep interactive targets at least 32 px in this compact desktop interface.

## AI News Video projects

The editing source of truth is `projects/<id>/storyboard.json` once Phase 4 creates it.

- Do not regenerate unchanged assets.
- Do not introduce facts not contained in `facts.json`.
- Every factual scene must reference valid fact IDs.
- Prefer real media for real events, charts for numbers, timelines for chronology, AI imagery for abstract concepts, and kinetic typography for hooks.
- Preview before final rendering and validate after modifications.
- Search the current repository and audited upstream sources before implementing a subsystem; follow `REUSE → ADAPT → EXTEND → WRITE NEW`.
- Never modify `.upstream/` or depend on it at runtime.

Phase 13 agent integrations use `newsvid.agent_tools` deterministic boundaries for Codex/Cursor discovery, project inspection, storyboard edits, validation, and rendering. Unrelated scene caches must be preserved.
