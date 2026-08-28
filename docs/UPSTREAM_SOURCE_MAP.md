# Upstream source map

Snapshots: Videogen `6134ccdb05a19b8c88bc6609eafe47aefee7adca`; Auto-Create-Video `8c2e04337ca7fb574692c5830dafde35ac2017cd`; html-video `c414ecc07f795add03807d5d9ce4baefd807cea2`; newsvid `453cd07bf1a53773471de89871729aa278c7f0de`.

| Capability | Primary source files inspected | Our boundary | Phase |
|---|---|---|---|
| Pipeline/checkpoint | Videogen `pipeline/orchestrator.py`, `pipeline/checkpoint.py` | `CheckpointStore`, future pipeline interface | 0 foundation, later execution |
| Project management | html-video `core/src/registry.ts`, `core/src/project.ts` | `ProjectManager` | 0 |
| Configuration/logging | Videogen `config.py`, `log.py`; current `src/main/diagnostics.ts` | `AppConfig`, `configure_logging` | 0 |
| CLI/doctor | html-video `cli/src/bin.ts`, `commands/doctor.ts`, `commands/project.ts`; newsvid `newsvid` | `newsvid.cli`, `collect_status` | 0 |
| LLM/Ollama | Videogen `clients/llm.py`, `retry.py`, `config.py`; newsvid `newsvid` (`init_ollama_client`, `verify_ollama_server`, model/prompt configuration) | `LLMProvider`, `OllamaProvider`, `OllamaConfig` | 2 |
| Structured facts | Videogen JSON parsing/schema checks and prompt infrastructure; no upstream grounded-facts implementation | `CandidateFacts`, `FactSet`, `FactExtractor`, `FactsCoordinator` | 2 |
| Vietnamese news script | Videogen `generators/script.py`, `processors/content_chunker.py`; Auto-Create-Video `render/script-schema.ts`, `pipeline.ts`; newsvid `generate_script` and TTS word-duration estimates | `CandidateScript`, `NewsScript`, `ScriptGenerator`, `ScriptCoordinator` | 3 |
| TTS | Videogen `clients/tts.py`, orchestrator/checkpoint; Auto-Create-Video `src/tts/*`, `pipeline.ts`; newsvid `tts.py` | `TTSProvider`, `PiperProvider`, `F5TTSProvider`, `TTSCoordinator` | 5 |
| Vietnamese pronunciation / audio cache | Auto-Create-Video narration/voice config and file reuse; no complete upstream normalizer | `normalize_vi`, external pronunciation YAML, `TTSManifest` | 5 |
| STT/alignment | Videogen `clients/stt.py`, `pipeline/orchestrator.py` stage 5, `types.py` | `AlignmentProvider`, loopback `WhisperXProvider`, `AlignmentCoordinator`, `WordsDocument` | 6 |
| Subtitles | Videogen `generators/subtitles.py`, `tests/test_subtitles.py`, `processors/subtitle_qa.py` | `generate_ass`, `SubtitleLayout`, safe-area/overflow report | 6 |
| FFmpeg | Videogen `assembler/*`; newsvid `vid.py`; current `src/main/tools.ts` and `composition-ffmpeg.ts` | Future centralized Python executor, existing Electron executor remains | 7/10 |
| Ken Burns | Videogen `assembler/ken_burns.py`; Auto-Create-Video `html-composer.ts` | Future static visual renderer | 7 |
| HyperFrames/GSAP | Auto-Create-Video `hyperframes-runner.ts`, `templates/animations.js`; html-video `adapter-hyperframes` | Future `HTMLRenderer` adapter | 8 |
| Chromium renderer | html-video engine adapters/CLI export path | Future scene renderer | 8 |
| ComfyUI | Videogen `clients/comfyui.py`, `docs/workflows/*` | Future `ComfyUIProvider` | 9 |
| Templates | Auto-Create-Video `render/script-schema.ts`, samples and templates; html-video template metadata YAML | Phase 4 template IDs in `VisualRouter`; renderer registry remains future | 4 mapping / 8 rendering |
| Content graph / frames | html-video `content-graph/src/index.ts`, `core/src/project.ts`, `core/src/types/index.ts` | `Storyboard`, `StoryboardScene`, ordered scene/frame model | 4 |
| Scene and visual routing | Auto-Create-Video scene schema; Videogen `entity_extractor.py`, `types.py` | `SceneType`, `VisualPlan`, `VisualProvenance`, `VisualRouter` | 4 |
| Agents/Codex/Cursor | html-video `runtime/src/detect.ts`, `spawn.ts`, `defs/*` | Future agent adapter | 13 |
| Studio | html-video `project-studio/public/index.html`, `studio-server.ts` | Future Electron tab consuming the same backend pipeline | 16 integration |
| URL security/static fetch | html-video `cli/src/fetch-source.ts` | `StaticFetcher`, `assert_public_http_url` | 1 |
| Article extraction | Videogen `processors/article_parser.py`; html-video `fetch-source.ts`; newsvid `extract_text_from_url` | `ArticleIngestor`, `extract_article` | 1 |
| Metadata/images | OpenGraph/JSON-LD and DOM patterns inspected across the three sources; no complete implementation | `Source`, `ArticleImage`, `ImageManifest` | 1 |
| Browser fallback | html-video Chromium/Playwright engine boundary | `PlaywrightFetcher` | 1 |

Phases 0–6 intentionally create no complete video renderer, visual asset generator, template runtime, agent or Studio module. WhisperX and F5-TTS remain optional adapters to isolated loopback services.
