# Third-party notices — AI News Video

Phases 0–10 were reviewed against these read-only upstream snapshots. The application has no runtime dependency on `.upstream/`.

## Auto-Create-Video

- Repository: https://github.com/hoquanghai/Auto-Create-Video
- Commit reviewed: `8c2e04337ca7fb574692c5830dafde35ac2017cd`
- Copyright: Copyright (c) 2026 Ho Quang Hai
- License: MIT; full text in `licenses/upstream/Auto-Create-Video-MIT.txt`.
- Phase 0–10 use: Phase 10 additionally adapts licensed sample-rate/channel normalization concepts from `audio-tools.ts`. No upstream TypeScript source or media asset is copied.

## html-video

- Repository: https://github.com/nexu-io/html-video
- Commit reviewed: `c414ecc07f795add03807d5d9ce4baefd807cea2`
- License: Apache License 2.0; full text in `licenses/upstream/html-video-Apache-2.0.txt`.
- Phase 0–10 use: Phase 10 additionally adapts the Apache-2.0 mixed-engine concat normalization rationale and FFmpeg export boundary into `FinalAssembler`.
- The upstream template attribution chain was reviewed in `ATTRIBUTIONS.md`; no templates or template assets are distributed through Phase 5.

## Videogen

- Repository: https://github.com/Juwebien/videogen
- Commit reviewed: `6134ccdb05a19b8c88bc6609eafe47aefee7adca`
- License: no license file was present in the reviewed snapshot.
- Phase 0–10 use: `REFERENCE_ONLY` at the source-license level. Phase 10 independently implements transition assembly after reviewing observable xfade/acrossfade and ASS-burn behavior because no license grant permits copying source. No source, workflow, model or asset was copied.

## newsvid

- Repository: https://github.com/sausheong/newsvid
- Commit reviewed: `453cd07bf1a53773471de89871729aa278c7f0de`.
- License: no license file was present in the reviewed snapshot.
- Phase 0–5 use: `REFERENCE_ONLY`. URL/LLM/news behavior plus Kokoro voice, WAV and narration flow were reviewed; no source, model or asset was copied.

## Phase 2 dependencies

Phase 2 adds no third-party dependency. It uses the already-noticed HTTPX transport and Pydantic schema validation. Videogen and newsvid remain reference-only because no license file was present in either reviewed snapshot.

Phase 3 adds no third-party dependency or license file. Auto-Create-Video remains attributed under MIT; Videogen and newsvid remain reference-only.

Phase 4 adds no third-party dependency or copied template asset. Existing html-video Apache-2.0 and Auto-Create-Video MIT notices cover the adapted representation and metadata concepts.

Phase 5 adds no Python dependency or copied voice/model. Piper and F5-TTS are optional external local runtimes whose models and licenses must be supplied separately by the operator.

Phase 6 adds no Python dependency or copied model/font. WhisperX is an optional isolated local runtime whose package, model and licenses must be supplied separately by the operator. ASS generation is implemented locally; no Videogen source was copied.

Phase 7 adds no Python dependency or copied image/media asset. It invokes the operator-installed FFmpeg/FFprobe already required by the application. Article images retain their source URLs in project provenance and remain subject to their publishers' rights and terms.

Phase 9 adds no third-party package, model or copied workflow. ComfyUI and its checkpoints are optional external local components installed and licensed separately by the operator. The project communicates only through ComfyUI's local HTTP surface.

Phase 10 adds no third-party dependency or copied media. It uses the operator-installed FFmpeg/FFprobe and the already-noticed Playwright/GSAP runtime. Existing upstream license texts remain sufficient; no new license file is required.

## Phase 8 JavaScript runtime dependencies

- Playwright 1.58.2 — Apache-2.0. It controls the locally installed Edge/Chromium runtime. Existing Playwright Apache-2.0 text is stored at `licenses/python/playwright-Apache-2.0.txt` and applies to the same upstream project.
- GSAP 3.14.2 — Standard "No Charge" GSAP License, not MIT/Apache. Official terms: https://gsap.com/community/standard-license/. Project-specific notice: `licenses/javascript/GSAP-3.14.2-NOTICE.md`.
- Phase 8 uses GSAP only inside predefined render templates; it does not expose a GSAP/Webflow-like visual animation builder.
- No html-video or Auto-Create-Video template asset is copied.

## Phase 1 Python dependencies

- Trafilatura 2.2.0 — Apache-2.0; `licenses/python/trafilatura-Apache-2.0.txt`.
- Beautiful Soup 4.15.0 — MIT; `licenses/python/beautifulsoup4-MIT.txt`.
- HTTPX 0.28.1 — BSD-3-Clause; `licenses/python/httpx-BSD-3-Clause.md`.
- Playwright is an optional browser fallback installed with `.[browser]`; Apache-2.0 license text is in `licenses/python/playwright-Apache-2.0.txt`.
