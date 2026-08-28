# Third-party notices — AI News Video

Phases 0–3 were reviewed against these read-only upstream snapshots. The application has no runtime dependency on `.upstream/`.

## Auto-Create-Video

- Repository: https://github.com/hoquanghai/Auto-Create-Video
- Commit reviewed: `8c2e04337ca7fb574692c5830dafde35ac2017cd`
- Copyright: Copyright (c) 2026 Ho Quang Hai
- License: MIT; full text in `licenses/upstream/Auto-Create-Video-MIT.txt`.
- Phase 0–3 use: Phase 3 adapts the licensed hook/body/outro schema concept into an independently implemented Python model; no TypeScript source or assets are copied.

## html-video

- Repository: https://github.com/nexu-io/html-video
- Commit reviewed: `c414ecc07f795add03807d5d9ce4baefd807cea2`
- License: Apache License 2.0; full text in `licenses/upstream/html-video-Apache-2.0.txt`.
- Phase 0–1 use: project persistence, doctor and public URL fetching/security concepts adapted into Python with project-specific validation, atomic writes, DNS/redirect checks and bounded responses.
- The upstream template attribution chain was reviewed in `ATTRIBUTIONS.md`; no templates or template assets are distributed in Phase 0.

## Videogen

- Repository: https://github.com/Juwebien/videogen
- Commit reviewed: `6134ccdb05a19b8c88bc6609eafe47aefee7adca`
- License: no license file was present in the reviewed snapshot.
- Phase 0–3 use: `REFERENCE_ONLY`. Article parsing, LLM JSON/retry/configuration, content pacing, and script prompt behavior were reviewed; no source or assets copied.

## newsvid

- Repository: https://github.com/sausheong/newsvid
- Commit reviewed: `453cd07bf1a53773471de89871729aa278c7f0de`.
- License: no license file was present in the reviewed snapshot.
- Phase 0–3 use: `REFERENCE_ONLY`. URL extraction, Ollama client/model/prompt, and generic news narration behavior were reviewed; no source or assets copied.

## Phase 2 dependencies

Phase 2 adds no third-party dependency. It uses the already-noticed HTTPX transport and Pydantic schema validation. Videogen and newsvid remain reference-only because no license file was present in either reviewed snapshot.

Phase 3 adds no third-party dependency or license file. Auto-Create-Video remains attributed under MIT; Videogen and newsvid remain reference-only.

## Phase 1 Python dependencies

- Trafilatura 2.2.0 — Apache-2.0; `licenses/python/trafilatura-Apache-2.0.txt`.
- Beautiful Soup 4.15.0 — MIT; `licenses/python/beautifulsoup4-MIT.txt`.
- HTTPX 0.28.1 — BSD-3-Clause; `licenses/python/httpx-BSD-3-Clause.md`.
- Playwright is an optional browser fallback installed with `.[browser]`; Apache-2.0 license text is in `licenses/python/playwright-Apache-2.0.txt`.
