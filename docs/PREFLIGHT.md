# Environment preflight

Every production task resolves its direct and transitive dependencies through the typed registry in `newsvid.doctor`. The same stable report schema powers CLI, API, job progress and the desktop Environment/Dependencies view.

## Commands

```powershell
.\.venv\Scripts\newsvid doctor --task render
.\.venv\Scripts\newsvid doctor --task tts --fix
.\.venv\Scripts\newsvid doctor --task preview --json --strict
```

Linux/macOS use `.venv/bin/newsvid`. `--fix` only synchronizes declared Python/Node packages, installs Playwright Chromium, or atomically downloads the known Piper voice. It never creates secrets, changes providers, installs privileged system packages, or starts an external service it does not own.

## Dependency matrix

| Task | Required dependencies | Conditional/optional |
| --- | --- | --- |
| facts, script | Python venv/packages, Ollama and configured model | none |
| visual | Python packages | ComfyUI + configured SDXL only for ComfyUI-routed scenes |
| TTS | Piper runtime, Vietnamese ONNX/config, UTF-8 WAV smoke | F5-TTS only when selected |
| alignment/subtitles | WhisperX health schema and configured model, Unicode font | none |
| scene | TTS, visuals/assets, Node packages, Chromium smoke, FFmpeg/FFprobe capabilities | ComfyUI only for generated scenes |
| preview/final render | scene dependencies, WhisperX, subtitles, libx264/libass | none |
| build/test/UI verify | declared Node/pnpm version, synchronized lockfile | browser for UI verification |

FFmpeg is checked for libx264, libass/subtitles, scale, overlay, zoompan, xfade, concat and aresample plus WAV, MP3, WebM and MP4 support. Preflight also encodes and probes a tiny real MP4. Chromium must launch headless, load a local HTML file and capture a frame.

## Services and errors

Ollama, WhisperX and ComfyUI checks validate response schemas and configured model/checkpoint availability. A listening port alone is not READY. Reports distinguish authentication failure, timeout, connection failure and incompatible service responses; query credentials are redacted.

WhisperX is external in the current architecture. Start an OpenAI-compatible loopback service exposing `/health`, `/v1/models`, and `/v1/audio/alignments`, with the configured model. ComfyUI is required only for scenes routed to it. CPU rendering and Piper work offline; LLM stages need a configured local Ollama model.

Status meanings: `READY`, `OPTIONAL_MISSING`, `FIXABLE`, `FIXING`, `BLOCKED`, `DEGRADED`, and `FAILED`. A blocked preflight stops before stage execution with one `PRECHECK_BLOCKED` root cause. Completed checkpoints are reconciled against non-empty, parseable artifacts and referenced files before resume.

## Platform notes

- Windows: executable paths with spaces/Unicode and `.exe` are passed as argument arrays with `shell=False`.
- Linux: install a full FFmpeg build and readable fonts under `/usr/share/fonts`.
- macOS: use a full FFmpeg build and readable fonts under `/System/Library/Fonts`; configure a compatible Chromium binary when system Edge is unavailable.
- All subprocess text and Vietnamese Piper input use UTF-8. No command depends on an implicit working directory.
