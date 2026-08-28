# Upstream source map

Snapshots: Videogen `6134ccdb05a19b8c88bc6609eafe47aefee7adca`; Auto-Create-Video `8c2e04337ca7fb574692c5830dafde35ac2017cd`; html-video `c414ecc07f795add03807d5d9ce4baefd807cea2`; newsvid `453cd07bf1a53773471de89871729aa278c7f0de`.

| Capability | Primary source files inspected | Our boundary | Phase |
|---|---|---|---|
| Pipeline/checkpoint | Videogen `pipeline/orchestrator.py`, `pipeline/checkpoint.py` | `CheckpointStore`, future pipeline interface | 0 foundation, later execution |
| Project management | html-video `core/src/registry.ts`, `core/src/project.ts` | `ProjectManager` | 0 |
| Configuration/logging | Videogen `config.py`, `log.py`; current `src/main/diagnostics.ts` | `AppConfig`, `configure_logging` | 0 |
| CLI/doctor | html-video `cli/src/bin.ts`, `commands/doctor.ts`, `commands/project.ts`; newsvid `newsvid` | `newsvid.cli`, `collect_status` | 0 |
| LLM/Ollama | Videogen `clients/llm.py`; newsvid `newsvid` | Future `LLMProvider` | 2 |
| TTS | Videogen `clients/tts.py`; Auto-Create-Video `src/tts/*`; newsvid `tts.py` | Future `TTSProvider` | 5 |
| STT/alignment | Videogen `clients/stt.py` | Future alignment provider | 6 |
| Subtitles | Videogen `generators/subtitles.py`, `processors/subtitle_qa.py` | Future subtitle package | 6 |
| FFmpeg | Videogen `assembler/*`; newsvid `vid.py`; current `src/main/tools.ts` and `composition-ffmpeg.ts` | Future centralized Python executor, existing Electron executor remains | 7/10 |
| Ken Burns | Videogen `assembler/ken_burns.py`; Auto-Create-Video `html-composer.ts` | Future static visual renderer | 7 |
| HyperFrames/GSAP | Auto-Create-Video `hyperframes-runner.ts`, `templates/animations.js`; html-video `adapter-hyperframes` | Future `HTMLRenderer` adapter | 8 |
| Chromium renderer | html-video engine adapters/CLI export path | Future scene renderer | 8 |
| ComfyUI | Videogen `clients/comfyui.py`, `docs/workflows/*` | Future `ComfyUIProvider` | 9 |
| Templates | Auto-Create-Video `render/templates/*`; html-video `templates/*` and metadata YAML | Future template registry | 8 |
| Content graph | html-video `content-graph/src/index.ts`, `core/src/project.ts` | Future storyboard schema/adapter | 4 |
| Agents/Codex/Cursor | html-video `runtime/src/detect.ts`, `spawn.ts`, `defs/*` | Future agent adapter | 13 |
| Studio | html-video `project-studio/public/index.html`, `studio-server.ts` | Future Electron tab consuming the same backend pipeline | 16 integration |
| URL security/static fetch | html-video `cli/src/fetch-source.ts` | `StaticFetcher`, `assert_public_http_url` | 1 |
| Article extraction | Videogen `processors/article_parser.py`; html-video `fetch-source.ts`; newsvid `extract_text_from_url` | `ArticleIngestor`, `extract_article` | 1 |
| Metadata/images | OpenGraph/JSON-LD and DOM patterns inspected across the three sources; no complete implementation | `Source`, `ArticleImage`, `ImageManifest` | 1 |
| Browser fallback | html-video Chromium/Playwright engine boundary | `PlaywrightFetcher` | 1 |

Phases 0–1 intentionally create no LLM, facts, TTS, STT, renderer, template, agent, content-graph or Studio module.
