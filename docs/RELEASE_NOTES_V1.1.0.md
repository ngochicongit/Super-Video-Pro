# Super Video Pro 1.1.0

V1.1 is a product-hardening release built on the frozen V1 architecture.

## Improvements

- Queue search and status filtering with visible shown/total counts.
- Safe removal of individual completed or cancelled jobs and bulk clearing of terminal history.
- “Show file” action for completed downloads through a validated main-process IPC boundary.
- App version displayed in the desktop header.
- Native completion/failure notifications with per-state deduplication.
- Collision-safe output naming: existing completed files are preserved and new downloads receive a numbered filename.
- Direct downloads infer a useful extension from their URL when the extracted title has none.
- Application version updated to 1.1.0 while retaining the V1 database and settings format.

## Compatibility

No database migration is required. Existing V1 queue state, settings, artifacts, partial downloads and user data remain compatible.
