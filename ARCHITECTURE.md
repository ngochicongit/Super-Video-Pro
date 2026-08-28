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
