# Super Video Pro 1.0.0

Super Video Pro V1 is a local-first Windows download manager for lawful media sources.

## Included

- Direct media, HLS, DASH, yt-dlp fallback, generic extraction, and isolated Browser Sniffer fallback.
- Persistent SQLite queue with concurrency/domain limits, pause, resume, cancel, retry, and restart recovery.
- Explicit `MediaArtifact` and `FinalArtifact` processing contracts with ffprobe validation.
- Single and batch input, quality selection, configurable destination/concurrency, and browser-cookie source selection.
- Sandboxed renderer with schema-validated IPC, safe credential storage, redacted diagnostics, SSRF protections, and privacy guidance.
- Bundled yt-dlp, ffmpeg, and ffprobe, plus atomic checksum-verified tool updates with rollback.
- Optional application update boundary using Electron Updater; a feed must be configured by the distributor.

## Verification

See `docs/VERIFICATION_REPORT.md` and `docs/RELEASE_CHECKLIST.md` for the audited test, packaging, clean-install, and release evidence.
