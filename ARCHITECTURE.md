# AI News Video architecture

The existing Electron/React/TypeScript application remains the only desktop frontend. The Python package at `packages/pipeline/src/newsvid` is the local business-logic foundation for the new article-to-video capability.

Phase 0 boundaries:

- `AppConfig` validates local paths and service endpoints from `config/app.yaml` and environment overrides.
- `ProjectManager` owns the `projects/<id>/` layout and rejects unsafe IDs.
- Pydantic models validate `project.json` and `checkpoint.json` at every load.
- `CheckpointStore` persists the canonical pipeline stages through atomic file replacement.
- `newsvid doctor` reports required and optional Windows dependencies without requiring external services during tests.
- `.upstream/` is audit input only and is never a runtime dependency.

Later stages must plug into these boundaries. They must not duplicate pipeline logic in Electron, and `storyboard.json` becomes the editing source of truth only when Phase 4 implements it.

See `docs/ARCHITECTURE.md` for the existing Electron architecture and `docs/UPSTREAM_SOURCE_MAP.md` for future adapter mapping.

## Phase 1 ingestion

`newsvid ingest` routes a public URL through a bounded static HTTP fetch and Trafilatura. If the result cannot produce a valid article, the optional Playwright adapter performs one guarded browser fetch and the same extractor validates its output. BeautifulSoup DOM heuristics are the final content reducer, not a separate unvalidated output path.

The coordinator atomically writes `source.json`, `article.md` and `images.json`, then completes the INGEST checkpoint with a deterministic fingerprint. Scraped scripts are parsed only as inert JSON-LD metadata and never reach the Electron renderer.

## Phase 2 grounded facts

`LLMProvider` keeps fact extraction independent of a particular model service. `OllamaProvider` implements Ollama's native `/api/chat` structured-output contract with bounded transient retries; malformed JSON and schema violations fail immediately.

`FactsCoordinator` reads only the persisted Phase 1 source and article, requests candidate facts, validates strict Pydantic schemas, checks every evidence quote against normalized `article.md`, and assigns deterministic IDs locally. It atomically writes `facts.json` and fingerprints article, source, prompt version, and provider configuration for safe cache reuse.

## Phase 3 Vietnamese news script

`ScriptGenerator` consumes only validated `facts.json` through the existing `LLMProvider`. Its structured prompt targets Vietnamese narration at 150 words per minute, defaults to 60 seconds, accepts 30–90 seconds, and supplies dedicated guidance for five news styles.

The generator assigns segment IDs locally, requires the first segment to be a grounded hook and the last to be an outro, rejects unresolved `fact_refs`, checks Vietnamese output, and enforces a 20% duration window. `ScriptCoordinator` fingerprints facts, prompt version, provider configuration, style, and duration before atomically writing `script.json`.

## Phase 4 storyboard and VisualRouter

`storyboard.json` is the only editing source of truth. The design adapts html-video's stable graph-node/frame IDs, 1:1 multi-frame representation, explicit duration and validate-before-write behavior into one ordered, news-specific scene list. A separate `content-graph.json` is deliberately not created because two editable representations could diverge.

Every scene retains its script segment ID, narration, duration and exact `fact_refs`. `VisualProvenance` distinguishes article, generated, stock, user, graphic and screenshot media and validates the fields required by each source type.

`VisualRouter` makes deterministic decisions from referenced facts and narration: hook → kinetic text; real person/event → article image or source screenshot; numbers → stat/chart/comparison; chronology → timeline; location → map; software/website → screenshot; abstract concept → ComfyUI illustration plan; outro → closing graphic. Phase 4 selects plans and template IDs only; it does not render visuals.

## Phase 5 Vietnamese TTS

`TTSProvider` isolates orchestration from speech engines. `PiperProvider` invokes the configured local executable with `shell=False`, validates the generated WAV and replaces the destination atomically. `F5TTSProvider` is an optional HTTP adapter to an isolated local service; importing or running the core pipeline does not require F5-TTS.

`normalize_vi.py` deterministically expands numbers, dates, years and percentages. Editable acronym, currency, unit and project-specific pronunciation rules live in `config/pronunciation_vi.yaml`, which is also packaged into the wheel as a fallback resource.

`TTSCoordinator` generates one `audio/scene_NNN.wav` per storyboard scene and records `audio/tts_manifest.json`. Each cache fingerprint includes original and normalized narration, voice, provider identity/configuration and pronunciation rules. Cache hits require a valid WAV whose SHA-256 still matches the manifest; changed or corrupted scenes regenerate independently. No timestamp, alignment, caption or subtitle artifact is produced in Phase 5.
