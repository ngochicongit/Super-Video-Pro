# Upstream reuse audit — Phases 0–1

Reviewed 2026-08-28. All repositories live under ignored `.upstream/` paths and are read-only references. Runtime code does not import from them.

## Classification

| Subsystem | Repository | Source | License | Strategy | Destination | Reason |
|---|---|---|---|---|---|---|
| Pipeline orchestration | Videogen | `src/videogen/pipeline/orchestrator.py`, `series_orchestrator.py` | No license found | REFERENCE_ONLY | Phase 0 architecture only | Valuable staged orchestration, but no license grant and full pipeline begins after Phase 0. |
| Checkpoint/resume | Videogen | `src/videogen/pipeline/checkpoint.py`, `tests/test_checkpoint.py` | No license found | REFERENCE_ONLY | `packages/pipeline/src/newsvid/checkpoint.py` | Concepts reviewed; implementation is new, atomic, validates corruption, and models the required stage set. |
| Cache | Videogen / html-video | checkpoint scene flags; `packages/core/src/asset-store.ts` | No license / Apache-2.0 | EXTEND (future) | Not created in Phase 0 | Project cache directory exists, but fingerprints and invalidation belong to later stages; no placeholder module. |
| Project management | html-video | `packages/core/src/registry.ts`, `project.ts`, `types/index.ts` | Apache-2.0 | ADAPT | `packages/pipeline/src/newsvid/project.py` | Adapted JSON-on-disk project store to Python, strict IDs, atomic writes and the master-plan directory model. |
| Core schemas | html-video / Auto-Create-Video | `packages/core/src/types/index.ts`; `src/render/script-schema.ts` | Apache-2.0 / MIT | ADAPT | `packages/pipeline/src/newsvid/schemas.py` | Reused strict boundary-validation approach; Phase 0 models only Project and Checkpoint. |
| Doctor | html-video | `packages/cli/src/commands/doctor.ts`, `packages/runtime/src/detect.ts` | Apache-2.0 | ADAPT | `packages/pipeline/src/newsvid/doctor.py` | Adapted command discovery/reporting to Windows dependencies and required/optional semantics. |
| CLI | html-video / newsvid | `packages/cli/src/bin.ts`, `commands/project.ts`; `newsvid` | Apache-2.0 / No license | ADAPT | `packages/pipeline/src/newsvid/cli.py` | Phase 0 exposes only doctor, project and checkpoint commands; generation commands are intentionally absent. |
| Structured logging | Videogen / current app | `src/videogen/log.py`; `src/main/diagnostics.ts` | No license / project code | EXTEND | `packages/pipeline/src/newsvid/logging.py` | Preserves the current application's JSON diagnostics boundary in a Python package; no upstream code copied. |
| LLM | Videogen / newsvid | `clients/llm.py`; `newsvid` | No license | REFERENCE_ONLY | Phase 2 | Provider boundaries and Ollama health patterns mapped; not implemented early. |
| TTS | Videogen / Auto-Create-Video / newsvid | `clients/tts.py`; `src/tts/*`; `tts.py` | No license / MIT / No license | REFERENCE_ONLY | Phase 5 | Actual provider integration is outside Phase 0. |
| STT/alignment | Videogen | `clients/stt.py` | No license | REFERENCE_ONLY | Phase 6 | Word timestamps mapped; no source copied. |
| Subtitles | Videogen | `generators/subtitles.py`, `processors/subtitle_qa.py` | No license | REFERENCE_ONLY | Phase 6 | ASS/karaoke and QA concepts mapped only. |
| FFmpeg / Ken Burns / transitions | Videogen | `assembler/encoder.py`, `compositor.py`, `ken_burns.py`, `transitions.py` | No license | REFERENCE_ONLY | Phases 7/10 | Current Electron app already centralizes tool execution; no premature Python renderer. |
| ComfyUI | Videogen | `clients/comfyui.py` | No license | REFERENCE_ONLY | Phase 9 | Workflow/API lifecycle mapped; no adapter created. |
| HyperFrames / GSAP / motion templates | Auto-Create-Video | `render/hyperframes-runner.ts`, `html-composer.ts`, `templates/*` | MIT | REFERENCE_ONLY | Phase 8 | Suitable implementation exists, but integrating it now would violate Phase 0 and no-placeholder rules. |
| Chromium renderer / templates | html-video | `packages/adapter-hyperframes`, `packages/adapter-remotion`, `templates/*` | Apache-2.0 plus template attributions | REFERENCE_ONLY | Phase 8 | Engine and provenance interfaces mapped for later inspection. |
| Content graph | html-video | `packages/content-graph/src/index.ts` | Apache-2.0 | REFERENCE_ONLY | Phase 4 | Storyboard concepts must not be implemented before Phase 4. |
| Codex / Cursor / agents | html-video | `packages/runtime/src/detect.ts`, `spawn.ts`, `defs/codex.ts`, `defs/cursor-agent.ts` | Apache-2.0 | REFERENCE_ONLY | Phase 13 | Agent detection/execution is mapped, not copied early. |
| Studio | html-video | `packages/project-studio/public/index.html`, `packages/cli/src/studio-server.ts` | Apache-2.0 | REFERENCE_ONLY | Phase 16 | UI is explicitly out of Phase 0; the Electron tab is therefore not added yet. |
| Public URL validation/fetch | html-video | `packages/cli/src/fetch-source.ts` | Apache-2.0 | ADAPT | `packages/article_ingest/src/newsvid_ingest/security.py`, `fetchers.py` | Adapted protocol/private-host guard, bounded redirects, timeout and browser-like user agent; extended with DNS classification, response size/type bounds and redirect revalidation. |
| Article content extraction | Videogen | `src/videogen/processors/article_parser.py`, `tests/test_article_parser.py` | No license found | REFERENCE_ONLY | `packages/article_ingest/src/newsvid_ingest/extractor.py` | Article/main/body selection, noise removal and section tests informed behavior; no source copied because no license grant. |
| HTML to Markdown | html-video | `packages/cli/src/fetch-source.ts` (`htmlToMarkdown`, `extractMainHtml`) | Apache-2.0 | ADAPT | `packages/article_ingest/src/newsvid_ingest/extractor.py` | Uses licensed source-handling concepts, but delegates primary extraction to Trafilatura and provides BeautifulSoup DOM heuristics instead of porting regex conversion. |
| URL article workflow | newsvid | `newsvid` (`extract_text_from_url`, `generate`) | No license found | REFERENCE_ONLY | `packages/pipeline/src/newsvid/ingestion.py`, CLI `ingest` | Simple request→BeautifulSoup→text flow reviewed; lacks metadata/images/security/fallback and cannot be copied without a license. |
| Metadata and image provenance | Videogen / html-video / newsvid | No complete upstream implementation found | Mixed | WRITE_NEW | `newsvid_ingest/models.py`, `extractor.py` | Required `source.json` and attributed `images.json` schemas, JSON-LD/OpenGraph resolution and relative URL handling are product-specific gaps. |
| Browser fallback | html-video rendering stack | adapter Chromium usage; no article fallback | Apache-2.0 | EXTEND | `newsvid_ingest/fetchers.py` (`PlaywrightFetcher`) | Reuses the audited browser boundary concept, adding article navigation, network request guards and optional-browser failure reporting. |

## WRITE_NEW justification

- `persistence.py`: neither licensed upstream implementation provides durable atomic JSON replacement plus Pydantic validation in the required Python/Windows architecture.
- `checkpoint.py`: Videogen's closest implementation has no license grant and its scene-flag model does not match the required eleven pipeline stages.
- Phase 0 tests: repository-specific acceptance tests are needed to prove path confinement, project layout, strict schemas and persisted checkpoints without external services.
- Phase 1 metadata/image extraction: none of the inspected upstreams produces the required source and attributed image manifests.
- Phase 1 Playwright article adapter: inspected browser code renders video or Studio previews; it does not safely fetch JS-dependent articles into the project's ingestion interface.

No upstream tests were copied verbatim. Videogen's article parser tests informed independently written fixture, noise-removal, section and fallback assertions.
