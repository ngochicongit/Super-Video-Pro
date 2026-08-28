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

## Phase 6 alignment and subtitles

`AlignmentProvider` isolates timestamp extraction. `WhisperXProvider` sends WAV, normalized transcript and `language=vi` to an OpenAI-compatible alignment endpoint restricted to loopback. Strict `WordTiming` and `SceneAlignment` models reject empty, reversed, overlapping or out-of-audio timestamps before `words.json` is persisted.

`AlignmentCoordinator` derives scene offsets from the validated TTS manifest, fingerprints storyboard/audio/provider/layout inputs, and updates the existing ALIGNMENT checkpoint. A matching complete checkpoint safely reuses `words.json`, ASS and its layout report.

The ASS generator adapts Videogen's punctuation grouping, timestamp formatting and word-level `\k` karaoke model. It adds Vietnamese-safe UTF-8 output, ASS escaping, approximately seven words per caption group, up to two display lines, adaptive font sizing, default 180 px top and 300 px bottom safe areas, and explicit overflow rejection. Phase 6 produces no video frames and does not burn subtitles into video.

## Phase 7 article-asset video

`ArticleImageCache` acquires only public HTTP(S) images already attributed in `images.json`. Downloads enforce supported image MIME types and a configured byte ceiling, use atomic replacement, persist source URL/content type/SHA-256, and reuse only intact cached files.

`FFmpegArticleRenderer` adapts Videogen's basic CPU path: aspect-fill scale and center crop, deterministic `zoompan` presets, and per-scene H.264/yuv420p video plus AAC narration. Commands use argument arrays with `shell=False`; ComfyUI is not imported or contacted.

## Phase 8 motion graphics

`SceneRenderer` is the single scene-rendering boundary. It retains `FFmpegArticleRenderer` for sourced article imagery and dispatches supported graphic scene types to `HyperFramesChromiumRenderer`; no parallel project or storyboard representation is introduced.

The motion adapter is a narrow adaptation of html-video's working HyperFrames renderer: generate self-contained HTML, freeze animation during page load, launch local Edge through Playwright, unfreeze and drive the GSAP timeline, record WebM at the requested viewport, and encode deterministic H.264/yuv420p MP4 through FFmpeg. The resulting silent motion clip is muxed with the Phase 5 scene WAV before entering the existing preview/final pipeline.

`MotionTemplateInput` validates structured inputs for hook, headline, stat-hero, chart, comparison, timeline, quote and outro. The visual system adapts Auto-Create-Video's Vietnamese social-news hierarchy and navy/cyan/purple palette while using local system fonts and embedded GSAP to avoid network-dependent rendering. Runtime and template fingerprints participate in scene/final cache invalidation.

## Phase 9 optional ComfyUI visuals

`ComfyUIProvider` is the only visual-generation service boundary. `HTTPComfyUIProvider` adapts the audited queue lifecycle (`/prompt` → bounded `/history/{prompt_id}` polling → `/view`) and loads only packaged workflow JSON for `news-image`, `background`, and `infographic`.

`VisualCoordinator` selects only storyboard visuals explicitly marked `source_type=generated` and `generator=comfyui`. Per-scene fingerprints cover prompt, deterministic seed, dimensions, provider configuration, checkpoint and exact workflow bytes. Generated bytes and `images/generated_manifest.json` are atomically replaced and SHA-256 verified before cache reuse. Partial successes remain resumable; a service failure records the `VISUALS` checkpoint as failed without altering the existing storyboard. Only an all-success run atomically adds project-relative generated provenance paths to `storyboard.json`. ComfyUI remains optional and is never started, stopped or bundled.

## Phase 10 full video assembly

There is one rendering chain: `SceneRenderer → RenderedScene → FinalAssembler`. `SceneRenderer` dispatches article/source images and generated ComfyUI images to the existing FFmpeg image renderer, while motion scenes use the existing Chromium/GSAP adapter. It persists one `scenes/manifest.json`; no second project or content-graph representation exists.

`FinalAssembler` is the only final-composition boundary. Before joining mixed renderer outputs it resets video/audio timestamps, normalizes every video to 1080×1920 at 30 fps/yuv420p, and normalizes every narration stream to 48 kHz stereo. It applies one N-scene FFmpeg graph using `xfade` plus `acrossfade`, or the normalized concat filter for hard cuts. `output/preview.mp4` contains voice, transitions and burned captions for meaningful visual review.

Preview assembly retimes later ASS dialogue events by accumulated transition overlap before burning captions. Finalization stream-copies that already validated preview into `output/final.mp4` without another lossy encode. Both preview and final must probe as exactly 1080×1920, 30 fps, H.264 and AAC before their checkpoints complete. The final fingerprint includes scene fingerprints, transition configuration, assembler version and ASS hash.
