# Super Video Pro 1.9.1

## Critical playback fix

- Fixed the editor disappearing shortly after playback starts.
- Root cause: the playhead synchronization effect returned `timeline.setTime()` as its React cleanup value. React attempted to invoke that non-function on the next time update and unmounted the renderer.
- The synchronization effect now has an explicit block body and returns no cleanup value.

## Automated coverage

- Added an Electron playback smoke hook that loads a real local project, starts playback, captures renderer errors and validates that the React root and professional timeline remain mounted.
- A six-second H.264/AAC fixture played past 3.5 seconds with the video still running, two React root children, the timeline present and zero runtime errors.
- Extracted source-trim resize, overlay bounds and animation-speed calculations into pure adapter functions.
- Added regression coverage for 2× trim mapping, source-duration clamping, complete logo containment and speed-to-cycle-duration behavior.
- `pnpm verify`: 33 suites and 128 tests passed.
- Packaged 1.9.1 playback smoke passed at 3.5 seconds with the video still playing, the React root and professional timeline mounted, and zero renderer errors.
- `release/Super Video Pro Setup 1.9.1.exe` was produced successfully (272,224,017 bytes).
- SHA-256: `549873ABE9534BD9EFA5E4219B0DA1CC3E66BDCE70A3797A7135917A61AE0310`.
- Authenticode status is `NotSigned`.

## Release boundary

This is a local Windows release candidate. No external publication or code-signing is claimed.
