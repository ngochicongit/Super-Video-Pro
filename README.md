# Super Video Pro

Local-first Windows desktop media and AI news production workspace built with Electron, React, TypeScript, Python/FastAPI and FFmpeg.

## Product overview

Super Video Pro combines three workflows in one resizable desktop application:

- inspect, download, validate and recover media jobs;
- compose clips, audio and multiple logos in a media-oriented timeline workspace;
- convert Vietnamese articles into grounded, narrated, captioned vertical news videos.

The renderer is presentation-only. Existing Electron IPC and the loopback NewsVid API remain the integration boundaries; SQLite, project files, FFmpeg and local AI services remain authoritative.

## Capabilities

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
- Multi-clip composition with trim, speed, waveform, audio, multi-logo overlays and a professional timeline.
- AI News projects with article ingestion, grounded facts, factual scripts, editable storyboards, Vietnamese TTS, captions, previews, final rendering and QA.
- Unified background progress, contextual recovery and service/model discovery.

## User interface

- **Download** provides single/batch inspection, variant choice and queue creation.
- **Compose** uses a media bin, preview canvas, properties inspector and multi-track timeline.
- **AI News Studio** provides project/content/scene/preview/QA workspaces and a one-click complete-video action.
- **History and Tasks** expose progress, retry, resume, cancellation and completed output.
- **Settings and Services** contain model/voice selection, dependencies, diagnostics, privacy, retention and updates.

The app is intended only for lawful downloads. It does not bypass DRM and does not promise compatibility with unsupported or access-controlled sites.

## Development

Requirements: Windows, Node 24+, pnpm 11 and Python 3.11–3.13. FFmpeg/FFprobe are required for media work; yt-dlp and Deno are prepared for packaged builds.

```powershell
pnpm install
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
pnpm dev
```

Verification and installer:

```powershell
pnpm verify
pnpm package
```

The NSIS installer is emitted under `release/`.

For a clean source build, `pnpm package` verifies TypeScript/tests/build, prepares runtime tools, packages the FastAPI backend and creates the NSIS installer. Large AI model weights are deliberately excluded.

## Architecture

```text
Electron Renderer
  -> UI adapters
    -> allowlisted Electron IPC / loopback FastAPI
      -> existing TypeScript services / Python coordinators
        -> SQLite / project JSON / FFmpeg / local AI services
```

Electron remains because the existing queue, filesystem, process, SQLite, IPC and NSIS lifecycle is verified. Clypra informed presentation patterns only; Tauri/Rust was not imported. Zustand owns local presentation state but does not replace server-owned job/project state. Migration is incremental so old and new surfaces can be parity-tested before removal.

## Configuration

Safe examples are documented in `.env.example`. Core values include project/config paths, loopback Ollama/WhisperX/ComfyUI endpoints, selected models, FFmpeg/FFprobe/Node and optional Chromium. Model and voice choices are also available as discovered selects in the application. Never commit `.env`, tokens, cookies, databases or private update-signing keys.

## Troubleshooting

- **Application does not start:** run `pnpm verify`; for an installed build export diagnostics from Settings.
- **Backend does not start/port 8787 conflict:** close the conflicting process and restart; the Electron lifecycle waits for `/health` before enabling Studio.
- **IPC unavailable:** use the packaged preload and do not enable renderer Node integration.
- **FFmpeg unavailable:** open Services and use dependency repair, or install/configure FFmpeg and FFprobe.
- **Model unavailable:** choose a detected model; Ollama/Piper/WhisperX can be set up automatically.
- **Media processing failed:** open Tasks, inspect the stage error and retry; unrelated jobs continue.
- **Installer problem:** verify SHA-256, use a writable install directory and note the current installer is not code-signed.
- **Permission problem:** choose user-owned input/output directories; do not run media work from protected system folders.
- **Service port conflict:** the service card identifies the endpoint; stop the unrelated listener or configure a different loopback port.

## AI News Video — Phases 0–10

The Python foundation is isolated from the Electron renderer and now supports the first complete basic article-to-video path: ingestion, grounded script/storyboard, Vietnamese WAV narration, word alignment, karaoke ASS subtitles, cached article imagery and vertical FFmpeg output without ComfyUI.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\newsvid doctor
.\.venv\Scripts\newsvid project create "Bản tin thử nghiệm"
.\.venv\Scripts\pytest
```

The upstream audit and provenance records are in `docs/UPSTREAM_REUSE_AUDIT.md`, `docs/UPSTREAM_SOURCE_MAP.md`, and `THIRD_PARTY_NOTICES.md`.

### Environment preflight and automatic repair

Production jobs run a typed dependency preflight before executing. Use `newsvid doctor --task render`, add `--json` for the stable API/UI schema, `--strict` for a non-zero blocked result, and `--fix` for safe idempotent repair. It capability-tests FFmpeg/FFprobe, Chromium, Piper Vietnamese TTS and configured service schemas/models instead of merely checking ports or version banners. See [docs/PREFLIGHT.md](docs/PREFLIGHT.md) for the stage graph, Windows/Linux/macOS setup, offline operation, provider conditions and error interpretation.

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

### Vietnamese TTS

```powershell
.\.venv\Scripts\newsvid tts <project-id>
.\.venv\Scripts\newsvid tts <project-id> --provider f5tts --voice female-vi
```

Piper is the default fast local provider and requires the configured Vietnamese ONNX model. F5-TTS is optional and accessed only through the configured isolated local HTTP service. Each scene produces `audio/scene_NNN.wav`; unchanged normalized narration, voice and provider configuration reuse the validated deterministic cache.

Pronunciation rules are editable in `config/pronunciation_vi.yaml`. They cover technology acronyms, currencies and units while `normalize_vi.py` handles numbers, dates, years and percentages.

### Word alignment and subtitles

```powershell
.\.venv\Scripts\newsvid align <project-id>
```

The command sends each validated scene WAV and normalized Vietnamese narration to the configured loopback WhisperX alignment service. It writes strict project-level `words.json`, `captions/subtitles.ass`, and `captions/subtitle_report.json`. Karaoke highlights follow word timings; captions prefer at most seven words per displayed group, adapt font size, preserve a 180 px top and 300 px bottom safe area, and fail instead of emitting overflowing captions.

### Full video rendering

```powershell
.\.venv\Scripts\newsvid preview <project-id> --transition dissolve
.\.venv\Scripts\newsvid render <project-id> --transition dissolve --transition-duration 0.35
```

The unified renderer accepts article/source images, Phase 8 motion graphics and Phase 9 generated images. Every scene includes its cached narration and becomes one validated `RenderedScene`. `FinalAssembler` normalizes mixed outputs, applies `none`, `fade`, `dissolve`, `wipeleft`, `wiperight`, or `slideup`, writes `output/preview.mp4`, retimes transition-aware captions, and writes `output/final.mp4` as 1080×1920, 30 fps, H.264/AAC. `render-article` remains only as a compatibility alias to this same pipeline.

### Motion graphics

Phase 8 integrates motion graphics into the same `SceneRenderer`. Graphic scenes selected in `storyboard.json` render through an html-video-derived Playwright/Chromium recording adapter with embedded GSAP timelines; article-image scenes continue through the Phase 7 FFmpeg Ken Burns path. Supported structured templates are `hook`, `headline`, `stat-hero`, `chart`, `comparison`, `timeline`, `quote`, and `outro`. Each template supports native 1080×1920 output and is muxed with the existing scene narration before normal preview, concatenation and subtitle composition.

### Optional ComfyUI visuals

```powershell
.\.venv\Scripts\newsvid visuals <project-id>
```

Phase 9 generates only storyboard scenes explicitly routed to ComfyUI, using `news-image`, `background`, or `infographic`. Generated files carry workflow/provider provenance and deterministic cache fingerprints; interrupted runs preserve completed assets and resume missing scenes. When ComfyUI is offline, the `VISUALS` checkpoint records an actionable failure while existing project JSON remains valid and unchanged. Article imagery and Phase 8 motion graphics continue to work without ComfyUI.

## Security boundary

The renderer has `nodeIntegration: false`, `contextIsolation: true`, and `sandbox: true`. It receives only the narrow API exposed by preload. Every request and response is checked against a Zod contract in the main process. Browser sniffing uses an ephemeral isolated session, denies popups, clears storage, and never receives a preload bridge.

## Data and privacy

Queue state, settings and logs stay under Electron's local `userData` directory. There is no telemetry. Sensitive values are protected with the OS-backed Electron `safeStorage` adapter and diagnostics redact credential-like fields and URL secrets.
