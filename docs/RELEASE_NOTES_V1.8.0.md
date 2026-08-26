# Super Video Pro 1.8.0

## Editor workflow

- Added direct left/right trim handles to every video clip with live timeline and preview feedback while dragging.
- Corrected timeline pointer mapping to use the media lane rather than the track-label column.
- Added persistent lock controls for video, audio and overlay tracks.
- Added audio mute control and guaranteed muted exports use FFmpeg `volume=0`.
- Added FFmpeg waveform rendering with a reusable cache fingerprinted by source path, size and modification time.
- Project save/load and undo/redo now preserve all track lock and mute states.

## Verification

- `pnpm verify`: 32 suites and 122 tests passed, including a real FFmpeg waveform cache test.
- Electron composition-tab visual smoke passed.
- `release/Super Video Pro Setup 1.8.0.exe` was produced successfully (271,415,736 bytes).
- SHA-256: `43537CF2610BCAFBF2BA8502F5AF772F19FC15185813AB2D10B4A441046F2AD8`.
- The packaged application remained alive during the local smoke window.
- Silent NSIS installation returned exit code `0`; the installed executable existed and remained alive during its smoke window.
- Silent uninstallation returned exit code `0` and removed the isolated installation directory.
- Authenticode status is `NotSigned`; this build is not code-signed.

## Release boundary

This is a local Windows release candidate. No external upload or publication is claimed.
