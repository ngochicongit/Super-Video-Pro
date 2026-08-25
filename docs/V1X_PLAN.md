# Super Video Pro - Master Plan and Progress

This is the single living document for task scope, completion rules, implementation notes and verification progress. New task-specific Markdown files must not be created; future work is appended here.

## Completion rules

A task is marked DONE only when implementation is complete, automated checks pass, proportional runtime verification is recorded, release state is explicit and temporary test artifacts are removed with `pnpm task:cleanup`.

## Product baseline

- V1.0: local-first queue, extraction pipeline, IPC schemas, persistence and artifact validation.
- V1.1: queue lifecycle, search/filter, file reveal, collision-safe outputs and notifications.
- V1.2: explicit inspect/download flow, structured diagnostics, Vietnamese locale, branded frameless window and interaction polish.
- V1.2.1: YouTube Deno runtime, embedded web client, cookie-lock fallback and Unicode output resolution.
- V1.2.2: X/Twitter cookie-aware inspection and yt-dlp support.
- V1.2.3: secure FxTwitter fallback for sensitive X posts unavailable to guest yt-dlp extraction.
- V1.2.4: compact UI, right-aligned native-style window controls and bounded task-artifact cleanup.
- V1.2.5: persistent link/control state, named plain-text diagnostics export and full technical review.

## Current task - Persistent UX state and diagnostics export

Status: DONE

Scope and acceptance:

1. Persist up to 30 recent valid links in SQLite and expose a compact recall/clear control.
2. Persist the URL draft, single/batch mode, queue query, status filter, diagnostics name and existing download controls when the user enables the remember-state checkbox.
3. Keep all persistence behind the validated IPC settings contract; bound every string and collection.
4. Export diagnostics as readable redacted `.txt`; accept an optional user name and use the existing dated base name when blank.
5. Complete automated, visual and packaged verification, then execute bounded cleanup.

## Whole-project technical review

Review basis: 26 source files / 486 lines before this task, 13 test files / 106 lines, production build, dependency audit and targeted static inspection.

### What is technically sound

- Main process owns network, filesystem, SQLite, external tools and validation; renderer stays sandboxed behind a schema-validated IPC boundary.
- `MediaResource`, `DownloadJob`, `MediaArtifact` and independent `FinalArtifact` contracts make pipeline state diagnosable.
- Queue recovery, per-domain concurrency, atomic direct downloads, artifact validation and failure isolation are appropriate for V1.x.
- Bundled tool checksum preparation, updater opt-in behavior, credential encryption helper and redacted diagnostics are good foundations.
- Real-site tests are kept outside the deterministic fixture suite, reducing CI flakiness.

### Technical objections and priorities

P0 before calling pause/resume fully reliable:

- External yt-dlp jobs use `--no-part`; aborting a job can discard resumable state while the UI advertises pause/resume. Preserve `.part` files and test restart semantics per extractor.
- yt-dlp progress currently maps percentage into `bytesDownloaded` with `totalBytes=100`; the contract says bytes, so UI and persisted metrics can be semantically wrong. Add a percent field or parse actual byte totals.

P1 reliability/security:

- `App.tsx`, extraction and downloader implementations are dense single-line modules. Split view components, site adapters and download engines before adding more providers.
- Generic HTML and manifest fetches need explicit response-size limits, shared timeouts and a consistent outbound URL policy to reduce memory and SSRF risk.
- FxTwitter restores compatibility but weakens pure local-first behavior and adds availability/privacy dependency. Keep it opt-in or self-hostable and surface provider use in UI.
- SQLite payload reads use unchecked `JSON.parse`; validate persisted jobs/artifacts/settings at read boundaries and quarantine corrupt rows instead of crashing startup.
- The update button has no packaged feed configuration and therefore appears functional while normally returning not configured. Hide it until configured or ship signed update metadata.

P2 maintainability/product:

- Replace broad `any` usage in DB, IPC handlers, preload responses and external JSON parsing with typed row/result adapters.
- Remove unused dependencies and dormant helpers (`react-hook-form`, resolver package, `electron-log`, vault/tool updater if not scheduled) or wire them into owned features.
- Pin manifest dependency ranges instead of `latest`; the lockfile is pinned today, but a fresh dependency refresh can introduce unreviewed breaking changes.
- Add component-level interaction tests for hydration, history recall, remember-state opt-out, debug filename fallback and keyboard operation.
- Add retention controls for job history, logs and SQLite backups; current cleanup covers test artifacts but not long-lived user-data growth.

### UI and UX objections

- Header actions become crowded near the minimum window width; move debug export into a secondary toolbar or overflow menu in a later UI pass.
- Quality labels mix `tbr` units from yt-dlp with manually normalized bitrates; normalize all rates to one unit before display.
- Errors are technically correct but often too generic. Map authentication, cookie-lock, provider outage and unsupported/DRM cases to actionable Vietnamese messages.
- Polling the full jobs/settings payload every 1.5 seconds is simple but wasteful and can cause visual churn. Push job events through IPC and refresh settings only on mutation.
- Link history needs privacy affordances beyond clear-all: per-item removal and optional automatic expiry.

### Functional and development roadmap

1. V1.2.5: finish state persistence and text diagnostics without widening provider scope.
2. V1.3: correct external pause/progress semantics, split downloader/extractor modules and add UI component tests.
3. V1.4: event-driven renderer updates, bounded fetch policy, validated DB reads and log/history retention.
4. V2 only if justified: self-hostable provider services, plugin adapters and signed update channel; do not add accounts/cloud/enterprise abstractions before evidence of need.

## V1.2.5 completion record

- Found and fixed a schema bug where `AppSettings.partial()` injected field defaults into patch requests, allowing an unrelated control save to reset history or other settings. `AppSettingsPatch` now has truly optional, strict, bounded fields.
- Persisted URL draft, single/batch mode, queue search, queue status filter, diagnostics filename, remember-state checkbox and existing download controls across restart.
- Added a 30-entry validated recent-link history with recall and clear-all controls; valid attempted links remain available for retry.
- Diagnostics export now produces readable redacted `.txt` lines, supports an optional sanitized filename and retains the dated legacy base name when blank.
- `pnpm audit --prod`: no known vulnerabilities.
- `pnpm verify`: PASS; TypeScript, 13 test files, 41 tests and production Electron/renderer build.
- Isolated packaged-app restart smoke: PASS; version 1.2.5, history, draft URL, debug name, checkbox, concurrency, search and status combobox restored from SQLite.
- NSIS clean install/uninstall: PASS; uninstall exit 0 and isolated directory removed.
- Final installer: `release/Super Video Pro Setup 1.2.5.exe`, 271,766,476 bytes, SHA-256 `A4653669145F08004A2E976FCFCAD71AFCAD8BCB214C38666C75CE6B1321391C`.
- Temporary runtime/profile/screenshot evidence removed with `pnpm task:cleanup`; source tests and release artifacts retained.

## Current task - Compact UI and task hygiene

Status: DONE

Scope:

1. Move minimize, maximize/restore and close controls to the right side of the custom header.
2. Replace circular traffic lights with compact flat controls and CSS-drawn symbols.
3. Reduce spacing, card padding and control sizing while retaining readability.
4. Preserve hover, active, focus-visible and reduced-motion behavior.
5. Consolidate new task/progress documentation into this file.
6. Add bounded cleanup automation for runtime evidence, isolated install-smoke directories and known temporary stream fragments.

Acceptance criteria:

- Window controls appear on the right in minimize, maximize/restore, close order.
- Header remains draggable outside interactive controls.
- UI passes typecheck, unit tests, production build and visual smoke inspection.
- Cleanup does not touch source tests, release installers or user-selected download directories.
- Task status changes to DONE only after verification and cleanup complete.

## Progress log

- 2026-08-24: UI density and right-aligned window controls implemented; verification pending.
- 2026-08-24: Added `pnpm task:cleanup` with explicit workspace-bounded targets; execution pending final evidence review.
- 2026-08-24: `pnpm verify` passed: TypeScript, 13 test files, 37 tests and production renderer/Electron build.
- 2026-08-24: Packaged V1.2.4 UI loaded from `app.asar`; visual review confirmed compact spacing and right-aligned minimize, maximize/restore and close controls. Temporary screenshot evidence was removed under the task cleanup rule.
- 2026-08-24: Final NSIS artifact `release/Super Video Pro Setup 1.2.4.exe` built successfully; size 271,765,253 bytes; SHA-256 `126C2C6744BD15DF370ECEC77845E8AA6AA55A223EFED02B58B0393393069A1B`.
- 2026-08-24: `pnpm task:cleanup` completed after verification; runtime evidence, isolated install-smoke directories and known stream fragments removed. Source tests and release installers were preserved.
- 2026-08-24: Registered `postpackage` so every successful future packaging run invokes the bounded cleanup automatically.

## V1.2.6 - Pause/resume and persistence integrity

Status: DONE

Completion rules:

1. A paused yt-dlp job must preserve a non-empty `.part` file and the next run must request the exact saved byte offset.
2. External progress must report downloaded and total byte counts from yt-dlp, never percentage values disguised as bytes.
3. FxTwitter fallback must default to OFF; enabling it must visibly disclose that the X post URL is sent to `api.fxtwitter.com`.
4. Invalid persisted job, artifact or setting payloads must be quarantined independently and must not prevent app startup.
5. Mark this task DONE only after verification, NSIS clean-install smoke and bounded cleanup pass.

Progress:

- Removed `--no-part`, retained `--continue`, and added yt-dlp byte progress templates with exact-total then estimated-total fallback.
- Fixed Windows abort handling to terminate the complete external-tool process tree before allowing a resume attempt.
- Local Range-server integration proof passed: first run preserved 1,047,552 bytes; second run requested byte 1,047,552 and completed the 25,165,824-byte file.
- Added FxTwitter consent to validated settings with default OFF and a visible third-party URL disclosure.
- Added SQLite payload validation and per-record quarantine for jobs, artifacts and settings; corrupt records no longer crash the healthy read/startup path.
- `pnpm verify`: PASS; TypeScript, 14 test files, 48 tests and production Electron/renderer build.
- Packaged-app visual/DOM smoke: PASS; version 1.2.6 loaded from `app.asar`, FxTwitter consent was unchecked by default, the third-party disclosure was visible, and the custom right-aligned window controls rendered correctly.
- NSIS clean install/uninstall: PASS; both processes exited 0 and the isolated install directory was removed.
- Final installer: `release/Super Video Pro Setup 1.2.6.exe`, 271,768,195 bytes, SHA-256 `DCB7083468C2D1DE588279B6C5955787EEDEAFCE1C829C63423D7CCEC8F42DD2`.
- Temporary proof server, partial media, isolated profile and screenshots were removed by the bounded task cleanup; source tests and release artifacts were retained.

## Evidence-first implementation baseline

Status: DONE

### Task Change Checklist

- [x] Acceptance criteria defined.
- [x] Affected and not-affected areas identified.
- [x] Existing tests pass.
- [x] Regression tests added where required.
- [x] DB, contract and IPC impact checked.
- [x] `pnpm verify` passes.

This is a lightweight task checklist, not an ISO, OS or enterprise governance layer. Composition, Visual Editor, `ProcessingJob`, `ProcessingQueue`, `QueryLayer` and `FeatureFlagService` remain frozen until current implementation boundaries justify them.

### Regression evidence

- Historical RED-before-fix evidence for the two P0 bugs does not exist because their regression tests were introduced after the implementation fix. Do not represent the current tests as having followed test-first development retroactively.
- Mutation check 1 deliberately restored `--no-part`; `tests/external-progress.test.ts` failed at `keeps resumable part files enabled`.
- Mutation check 2 deliberately restored the legacy percent-as-bytes behavior; the same suite failed because `[download] 50.0%` produced `{bytesDownloaded:50,totalBytes:100}` instead of being rejected.
- Both mutations were reverted immediately. The checks prove the current tests are sensitive to recurrence of both P0 defects.

### Enforcement status

- General change enforcement: MANUAL. Developers still choose when to run `pnpm verify`; this is a verification procedure, not a universal CI firewall.
- Release enforcement: AUTOMATED LOCAL GATE. `pnpm package` now begins with `pnpm verify`; a typecheck, test or build failure stops NSIS packaging.
- CI and commit hooks remain unimplemented and are not claimed.
- Release-gate proof: `pnpm package` ran `pnpm verify` first (14 test files, 48 tests, typecheck and production build all passed), then produced the NSIS artifact and ran bounded cleanup. Packaging exited 0.

### Measured codebase baseline

Generated by `pnpm metrics` using a deterministic lexical TypeScript heuristic. Function and cyclomatic counts are directional baselines, not compiler-semantic measurements.

| Metric | Current value |
| --- | ---: |
| Source files | 24 |
| Test files | 14 |
| Non-empty LOC | 547 |
| Function-like constructs | 366 |
| Branch tokens | 330 |
| Explicit `any` occurrences | 16 |
| IPC channels | 22 |
| Production DB query tokens | 29 |
| Test cases | 48 |

Largest modules by non-empty LOC are `extraction.ts` (56), `jobs.ts` (47), `contracts.ts` (47), `db.ts` (41), `App.tsx` (40) and `downloader.ts` (34). LOC understates the real density because several modules contain long one-line implementations.

Highest measured function complexity is `App` at 39, followed by `registerIpc` and `JobManager.execute` at 14, `resolveExternalOutput` at 13, and `downloadHttp` at 10. This confirms that `App.tsx`, extraction and downloader deserve focused P1 decomposition without introducing new product abstractions.

### Processing abstraction decision

No production or test reference to `ProcessingJob`, `ProcessingQueue`, Composition, `QueryLayer` or `FeatureFlagService` exists. Current evidence therefore does not justify implementing them. Next work should split renderer behavior, extraction adapters and download engines, then remove typed-boundary `any` usage. Re-evaluate processing abstractions only when a real second processing workflow creates shared lifecycle requirements.

## V1.2.7 - P1 decomposition without rewrite

Status: DONE

Guardrails applied:

- Each extraction documented an existing input/output boundary before edits.
- Existing test logic remained unchanged; every step ran `pnpm verify` before continuing.
- No `Manager`, `Service`, `Bus` or `Registry` abstraction was introduced. One `IpcInput` helper type maps already-validated Zod channel inputs.
- Composition, ProcessingJob/Queue, QueryLayer, FeatureFlagService and Visual Editor remain frozen.

Extraction sequence and metrics:

| Step | Source files | Non-empty LOC | Function-like | Branches | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Baseline | 24 | 547 | 366 | 330 | `App` 39; `registerIpc` 14; `execute` 14; resolver 13 |
| External output resolver | 25 | 572 | 367 | 330 | Resolver moved to an isolated module; measured complexity 11 |
| IPC domains | 29 | 599 | 370 | 330 | 22 channels unchanged; `registerIpc` left the hotspot list |
| Job execution phases | 29 | 615 | 372 | 330 | `execute` reduced to orchestration and left the hotspot list |
| Renderer regions | 34 | 653 | 383 | 330 | `App` reduced from 39 to 19 |

LOC increased because dense one-line behavior was expanded into explicit module boundaries. Branch count stayed at 330, supporting that this was decomposition rather than behavior deletion.

Extracted boundaries:

- `resolveExternalOutput(destinationDir, candidates, sourceUrl, startedAt) -> final absolute path` moved to `external-output.ts`.
- IPC registration still validates input and output centrally; handler construction is grouped into app/window, job/media and runtime/update domains.
- Job execution retains the same state lifecycle but delegates preparation/download, validation/completion and failure/retry handling to private methods.
- Renderer state orchestration remains in `App`; existing header, composer, queue, job row and window bar regions became components without changing CSS selectors or user flows.

Gate status:

- Workspace is not a Git repository (`git rev-parse` returned no worktree), so installing a pre-commit hook here would be fake enforcement. No hook was created.
- General edits still rely on manual `pnpm verify`; release packaging remains automatically blocked by the verify-first `pnpm package` script.
- Visual smoke from the production build passed with bridge ready, version rendered, all controls present and the existing layout unchanged.
- Final `pnpm package` gate passed: typecheck, 14 test files, 48 tests, production build, NSIS packaging and bounded cleanup all completed successfully.
- Packaged `app.asar` smoke passed: bridge `object`, document `complete`, and version 1.2.7 rendered.
- Clean NSIS install/uninstall passed with exit code 0; the isolated install directory was removed.
- Final installer: `release/Super Video Pro Setup 1.2.7.exe`, 271,766,493 bytes, SHA-256 `0D5CD5AD20BB2A447CA126BDE3DB0D63A4E34A40EFECF00891745552451C10C3`.

## V1.2.8 - Remaining V1.x reliability and maintainability tasks

Status: DONE

Implemented scope:

- Split extraction into pipeline, shared types and direct/manifest/generic, yt-dlp, FxTwitter and browser adapters.
- Split downloading into HTTP and external engines with shared progress and output-reservation modules. Existing public imports remain compatible through barrel modules.
- Added a shared outbound network policy: HTTP(S)-only, no URL credentials, blocks unspecified/link-local metadata targets, validates every redirect, limits redirects, applies request timeouts and enforces HTML/JSON limits by streamed bytes rather than character count.
- Generic HTML is limited to 2,000,000 bytes; FxTwitter JSON is limited to 1,000,000 bytes. Discovered and sniffed media URLs pass the same URL policy.
- Added explicit update capability to `app:get-info`; the update button is hidden when no packaged feed is configured instead of advertising a non-working action.
- Replaced renderer polling with validated `jobs:changed` events through the preload bridge. Initial jobs/settings load remains; subsequent job mutations update individual store entries.
- Added configurable retention controls: terminal job history 1-3650 days, daily diagnostic logs 1-365 days and SQLite migration backups 1-10 copies. Defaults are 90 days, 30 days and 3 backups.
- Added per-link history removal in addition to clear-all.
- Normalized FxTwitter bitrate from bits/second to the UI contract's kbps unit.
- Added actionable Vietnamese error guidance for invalid/unsupported media, timeouts, low disk, missing tools, invalid final media, locked browser cookie databases and provider access failures.
- Removed unused `@hookform/resolvers`, `react-hook-form`, `electron-log` and dormant `vault.ts`. All remaining dependency versions are pinned; the atomic tool updater remains because it has owned checksum/rollback tests.
- Removed explicit `any` from production source boundaries. Metrics now distinguish production and test-only occurrences.

Verification evidence:

- `pnpm verify`: PASS; TypeScript, 19 test files, 68 tests and production renderer/Electron build.
- New coverage includes outbound URL/byte boundaries, update capability schema, renderer event upsert behavior, job/log/backup retention, bitrate normalization, actionable errors, hydration, recent-link handling, remember-state opt-out and diagnostics filename fallback.
- `pnpm audit --prod`: no known vulnerabilities.
- Current metrics: 45 source files, 19 test files, 743 non-empty LOC, 368 branch tokens, 22 IPC channels, 30 DB query tokens, production explicit `any` count 0, test-only explicit `any` count 7. `App` measured complexity decreased from 19 to 18.
- Development visual smoke: PASS; bridge ready, retention controls rendered, update action absent with no feed, and the compact layout remained usable at 1180x760.
- Release gate: PASS; `pnpm package` reran all 68 tests, typecheck and production build before creating NSIS.
- Packaged `app.asar` smoke: PASS; bridge `object`, document `complete`, version 1.2.8 rendered, update action hidden without a feed and retention controls present.
- Clean NSIS install/uninstall: PASS with exit code 0; isolated installation directory removed.
- Final installer: `release/Super Video Pro Setup 1.2.8.exe`, 271,391,520 bytes, SHA-256 `0B14313990A4D8A0C4E1D05C7C59E5317F0CD93A304DC5CCC33B1B132383D30E`.
- Temporary screenshots, profiles and install-smoke directories were removed by bounded cleanup. Source tests and release artifacts were retained.

Deferred by evidence, not incomplete implementation:

- No signed update channel is shipped because no feed/signing infrastructure has been provided; the UI now accurately hides the capability.
- Composition, ProcessingJob/Queue, QueryLayer, FeatureFlagService and Visual Editor remain frozen until a second real workflow requires them.
- Git commit/CI enforcement remains unavailable because this workspace is not a Git worktree; release packaging itself is verify-gated.

## V1.2.9 - Delivery foundation and signed-update infrastructure

Status: IN PROGRESS

### Phase 1 - Git and CI gate

Status: DONE

- Initialized the workspace as a Git repository on `main` and configured the repository-local `core.hooksPath` to `.githooks`.
- Added a pre-commit hook that runs the complete `pnpm verify` gate. Hook files are forced to LF line endings for Git for Windows compatibility.
- Added a least-privilege Windows GitHub Actions workflow for pushes and pull requests: Node.js 24, pinned pnpm 11.19.0, FFmpeg fixture dependency, frozen-lockfile install, full verification, production audit and codebase metrics.
- Generated and runtime-only trees remain excluded from Git: dependencies, builds, installers, outputs, coverage, SQLite runtime state and bundled tool binaries.
- Local gate result: PASS; 21 test files, 74 tests, typecheck and production build. Production dependency audit reports no known vulnerabilities.
- Hosted clean-checkout gate: PASS in GitHub Actions `Verify` run #7 at commit `1f48029`; Node/pnpm, portable FFmpeg, pinned runtime tools, all tests, build, production audit and metrics completed in 1 minute 13 seconds.

### Phase 2a - Signed update metadata (certificate-independent)

Status: IMPLEMENTED AND TESTED; NOT YET ENABLED FOR RUNTIME UPDATE DELIVERY

- Added a strict versioned manifest contract containing channel, version, publication time, HTTPS installer URL, SHA-256, byte size and optional compatibility/release-note metadata.
- Added deterministic canonical serialization and Ed25519 signature verification. Unknown fields, insecure URLs and tampered metadata are rejected.
- Added release-side signing over the same validated canonical payload; private keys remain caller-provided and are never generated or persisted by the application.
- Added HTTPS-only manifest retrieval through the shared outbound policy with redirect validation, timeout and a 64 KiB streamed response limit. Metadata is not returned until its Ed25519 signature verifies.
- Added streaming installer verification for exact byte size and SHA-256 before any future handoff to installation.
- Added tests for authentic manifests, signature tampering, invalid schema/URL and installer integrity.
- No private key or certificate is stored in the repository. Existing automatic-update UI remains disabled unless separately configured; this phase does not claim OS code signing or a secure end-to-end update channel.
- Added a manual, least-privilege release-candidate workflow. It builds the current Windows installer, creates Ed25519-signed metadata from a repository secret, verifies the signature immediately and uploads an immutable seven-day artifact bundle.
- The candidate workflow does not create a GitHub Release, publish a feed or enable automatic installation. Its installer remains unsigned at the OS level until Phase 2b credentials exist.

### Remaining gates

- Phase 2b requires Windows/macOS signing identities and CI secrets; automatic installation stays disabled until that work is complete.
- Evidence collection and thresholds must be implemented before Composition is opened.
- ProcessingQueue requires a real Composition workflow; Visual Editor requires the previously agreed usage thresholds. These conditional STOP gates remain active.

### Small delivery task - Create and push the GitHub repository

Status: CI COMPLETE; BRANCH PROTECTION REMAINS USER ACTION

Goal: publish the existing local `main` branch so the hosted verification workflow can run. The current local commit is `bd5b805`; no Git remote is configured yet.

Completion checklist:

- [x] Create a new empty GitHub repository. Do not initialize it with README, `.gitignore` or license because those files already exist locally.
- [x] Choose repository visibility intentionally; the repository is currently Public.
- [x] Configure `origin` as `https://github.com/ngochicongit/Super-Video-Pro.git`.
- [x] Confirm fetch and push target the intended repository.
- [x] Push local `main` and configure upstream tracking.
- [x] Complete a successful hosted `Verify` workflow on a clean Windows runner.
- [ ] Protect `main` after the first green run: require pull requests and require the `verify` status check before merge.
- [x] Confirm `git status` is clean, `main` tracks `origin/main`, and hosted `Verify` run #7 is green.

Verified on 2026-08-25: publication moved to the Public repository `ngochicongit/Super-Video-Pro`. Hosted clean-checkout runs exposed bootstrap assumptions in sequence: premature pnpm caching, missing ignored runtime tools and Chocolatey shims. Run #7 at commit `1f48029` passed after CI adopted deterministic setup and resolved the real portable executable from `Chocolatey\lib`. Only optional branch-protection configuration remains outside the codebase.

Safety rules:

- Never place access tokens, signing private keys, certificates, cookies or `.env` values in the repository.
- Do not use `git push --force` for the initial publication.
- If GitHub created an initial commit by mistake, stop and reconcile histories instead of forcing the local branch over it.
- Release installers and runtime tools remain ignored; publish them later through GitHub Releases or another signed release channel, not normal Git history.

### Evidence infrastructure before Composition

Status: IMPLEMENTED ON FEATURE BRANCH; OPT-IN COLLECTION ACTIVATED

- Added SQLite migration v2 with daily aggregate counters only. The table stores `day`, a closed event name and a count; it cannot store URLs, file paths, media titles or arbitrary metadata.
- Added a closed event vocabulary for composition intent, multi-input intent, completed exports and builder abandonment.
- Locked the initial dogfooding gate before collecting data: at least 3 active days, 10 multi-input intents, 5 completed exports and no more than 50% builder abandonment.
- The gate evaluator defaults to closed and has coverage for aggregation and below-threshold behavior.
- Gate coverage proves all thresholds must be met across at least three active days and that abandonment above 50% keeps the gate closed even when volume thresholds pass.
- Added an explicit, default-OFF local evidence opt-in and a visible Composition research probe. Recording is possible only after opt-in and only through a strict `single`/`multi` intent IPC schema; arbitrary fields such as URLs are rejected.
- Added an on-demand TXT export containing aggregate counts, active-day counts, bounce rate and gate progress. The export contains no URLs, paths, media titles or file content.
- Composition, ProcessingQueue and Visual Editor remain STOPPED; infrastructure existence is not evidence that the thresholds have been met.
