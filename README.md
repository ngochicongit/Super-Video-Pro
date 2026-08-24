# Super Video Pro

Local-first Windows desktop download manager built with Electron, React and TypeScript.

## V1.2 capabilities

- Persistent priority queue with concurrency and per-domain isolation.
- Pause, resume, cancel, retry and restart recovery.
- Ordered extraction: manifest/direct → yt-dlp → generic HTML → isolated browser sniffing.
- Direct HTTP resume through `.part` files; HLS/DASH through FFmpeg; complex sites through yt-dlp.
- Final file gate using size checks and FFprobe when available.
- Schema-validated, allowlisted renderer↔main IPC.
- SQLite persistence through the Electron/Node runtime—no native addon ABI dependency.
- OS-encrypted credential vault adapter and redacted local diagnostics.
- Searchable/filterable queue history with safe terminal-job cleanup and Explorer reveal.
- Collision-safe filenames, native completion/failure notifications and visible app version.
- Explicit inspect-to-download flow, Vietnamese locale catalog and structured local operation logs.
- Frameless branded window with custom controls, smooth interaction states and a dedicated application icon.

The app is intended only for lawful downloads. It does not bypass DRM and does not promise compatibility with unsupported or access-controlled sites.

## Development

Requirements: Node 24+, pnpm 11. Optional runtime tools: `yt-dlp`, `ffmpeg`, and `ffprobe` on `PATH`.

```powershell
pnpm install
pnpm dev
```

Verification and installer:

```powershell
pnpm verify
pnpm package
```

The NSIS installer is emitted under `release/`.

## Security boundary

The renderer has `nodeIntegration: false`, `contextIsolation: true`, and `sandbox: true`. It receives only the narrow API exposed by preload. Every request and response is checked against a Zod contract in the main process. Browser sniffing uses an ephemeral isolated session, denies popups, clears storage, and never receives a preload bridge.

## Data and privacy

Queue state, settings and logs stay under Electron's local `userData` directory. There is no telemetry. Sensitive values are protected with the OS-backed Electron `safeStorage` adapter and diagnostics redact credential-like fields and URL secrets.
