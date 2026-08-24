# V1 architecture

The main process owns network access, processes, SQLite, filesystem operations, tool discovery and validation. The renderer owns presentation state only. Preload exposes one generic `invoke` function, but the main process accepts only channels in `ipcContract` and validates both input and output.

`MediaResource` is a normalized discovery result. `DownloadJob` persists user intent and lifecycle. `MediaArtifact` describes physical intermediate/downloaded output and its validation. `FinalArtifact` is an independent user-facing contract that references its source artifact IDs; it does not inherit transient validation or intermediate paths.

Unknown external error codes are handled by `normalizeError()`: the stable public code becomes `UNKNOWN`, while `rawCode`, stage and safe diagnostic context remain available. This preserves forward compatibility.

The queue restores unsafe in-flight states to `queued` after restart. A job failure never stops another job. Concurrency is bounded globally and per domain. Final completion occurs only after validation.

## Extraction order

1. Manifest/direct recognition.
2. yt-dlp normalized adapter, when installed.
3. Generic HTML discovery.
4. Ephemeral sandboxed browser sniffer.

Recorded/pure fixtures and a local HTTP fixture test run in normal CI. Real-site smoke testing is intentionally separate because it is volatile and externally controlled.
