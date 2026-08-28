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

## AI News Video — Phases 0–4

The Python foundation is isolated from the Electron renderer and exposes project/checkpoint management, article ingestion, grounded facts, Vietnamese scripts, and an editable visual storyboard. It intentionally does not generate speech or video yet.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\newsvid doctor
.\.venv\Scripts\newsvid project create "Bản tin thử nghiệm"
.\.venv\Scripts\pytest
```

The upstream audit and provenance records are in `docs/UPSTREAM_REUSE_AUDIT.md`, `docs/UPSTREAM_SOURCE_MAP.md`, and `THIRD_PARTY_NOTICES.md`.

### Article ingestion

```powershell
.\.venv\Scripts\newsvid ingest "https://example.com/article"
.\.venv\Scripts\newsvid ingest tests\fixtures\article_vi.html --source-url "https://publisher.example/article"
```

The command creates a project containing validated `source.json`, `article.md`, and `images.json`. Static extraction is the default. Install the optional JS-page fallback with `pip install -e ".[browser]"` followed by `playwright install chromium`.

### Grounded facts

With local Ollama running and the configured model installed:

```powershell
.\.venv\Scripts\newsvid facts <project-id>
```

The command creates schema-validated `facts.json`. Each fact has a deterministic ID, claim, verbatim article evidence, importance, confidence, and source metadata. Invalid or ungrounded model output fails the FACTS checkpoint without replacing a valid artifact.

### Vietnamese news script

```powershell
.\.venv\Scripts\newsvid script <project-id>
.\.venv\Scripts\newsvid script <project-id> --duration 90 --style documentary
```

The default is a 60-second `breaking-news` script. Durations from 30–90 seconds and the styles `breaking-news`, `tech-news`, `finance-news`, `explainer`, and `documentary` are supported. Every segment must resolve its `fact_refs` against `facts.json` before `script.json` is written.

### Storyboard and visual routing

```powershell
.\.venv\Scripts\newsvid storyboard <project-id>
```

`storyboard.json` is the sole editing source of truth. It preserves narration, timing and `fact_refs`, and records a template plus visual provenance for every scene. The deterministic router uses article imagery for real people/events, graphics for numbers and chronology, screenshots for software/source fallback, and generated illustration only for abstract concepts.

## Security boundary

The renderer has `nodeIntegration: false`, `contextIsolation: true`, and `sandbox: true`. It receives only the narrow API exposed by preload. Every request and response is checked against a Zod contract in the main process. Browser sniffing uses an ephemeral isolated session, denies popups, clears storage, and never receives a preload bridge.

## Data and privacy

Queue state, settings and logs stay under Electron's local `userData` directory. There is no telemetry. Sensitive values are protected with the OS-backed Electron `safeStorage` adapter and diagnostics redact credential-like fields and URL secrets.
