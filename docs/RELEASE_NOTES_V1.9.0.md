# Super Video Pro 1.9.0

## Hybrid professional timeline

- Replaced the hand-built timeline interaction surface with `@xzdarcy/react-timeline-editor` 1.0.0.
- Added library-managed action dragging, edge resizing, cursor scrubbing, drag guides, grid snapping and edge auto-scroll.
- Added an AiCut-inspired adapter with a canonical 30 fps timebase, deterministic clip ordering and one undo checkpoint per pointer interaction.
- Preserved the existing Electron/React UI, project persistence, lock/mute state, waveform cache and FFmpeg export contracts.
- Video resize maps back to source trim values at the active clip speed; overlay move/resize maps to timeline start/end.

## Dependency boundary

- AiCut 0.8.6 is not available from the public npm registry; its package manifest targets a private AWS CodeArtifact registry. It is not bundled.
- No AiCut source file was copied. Design attribution and dependency details are recorded in `docs/THIRD_PARTY_NOTICES.md`.
- Production dependency audit reports zero known vulnerabilities.

## Verification

- `pnpm verify`: 33 suites and 124 tests passed.
- Electron composition-tab visual smoke passed with the virtualized timeline.
- `release/Super Video Pro Setup 1.9.0.exe` was produced successfully (272,224,344 bytes).
- SHA-256: `C400CCB4DDA430E7BF89EE6EB8C7577795C3E87FDE2FC94A2A82BBE5FB04BF4E`.
- The packaged application remained alive during its smoke window.
- Authenticode status is `NotSigned`.

## Release boundary

This is a local Windows release candidate. No external publication or code-signing is claimed.
