# Upstream reuse audit — Phase 0

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

## WRITE_NEW justification

- `persistence.py`: neither licensed upstream implementation provides durable atomic JSON replacement plus Pydantic validation in the required Python/Windows architecture.
- `checkpoint.py`: Videogen's closest implementation has no license grant and its scene-flag model does not match the required eleven pipeline stages.
- Phase 0 tests: repository-specific acceptance tests are needed to prove path confinement, project layout, strict schemas and persisted checkpoints without external services.

No upstream tests were copied verbatim. Their assertions around persistence/resume informed independently written Phase 0 acceptance tests.
