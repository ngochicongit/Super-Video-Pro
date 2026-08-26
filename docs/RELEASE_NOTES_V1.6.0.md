# Super Video Pro 1.6.0

## Timeline rendering

- Trim the start and end of every video clip independently.
- Change individual clip playback speed from 0.25x to 4x.
- Set audio gain from muted to 200 percent.
- Set exact start and end times for every logo overlay.
- Timeline clip widths and total project duration reflect trim and speed changes.
- Preview seeking maps edited timeline time back to the source clip time.

## Engine and validation

- Adds a version-compatible edit contract while preserving legacy composition jobs.
- FFmpeg now applies trim, PTS speed adjustment, normalization, concatenation and timed overlays in render order.
- Validates ordered clip paths, trim ranges, overlay ranges, speed and audio gain.
- Real integration coverage proves an edited four-second source exports as a one-second timeline.

## Release evidence

- Installer: `Super Video Pro Setup 1.6.0.exe`
- Size: `271412771` bytes
- SHA-256: `3DC302378167461DB668D5AB87188FFA7BE02DA65EE072A36880226BD38248E3`
- Typecheck, 117 tests, production build and packaged-app smoke passed.
- Authenticode: not signed.
