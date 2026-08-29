# BANGBANGVIDEO UI Architecture and Repository Assessment

Date: 2026-08-29
Scope: current Electron downloader/composer plus AI News Studio
Decision rule: functional fit and workflow fit take precedence over appearance.

## 1. Executive summary

BANGBANGVIDEO is a local-first Windows media workstation with three distinct but connected jobs:

1. inspect and download one or many media URLs through a persistent queue;
2. compose downloaded/local clips, audio and multiple logos with FFmpeg;
3. turn a Vietnamese article into a grounded, narrated, captioned vertical news video.

The correct UI pattern is therefore a **hybrid desktop media workspace and automation control panel**. A generic admin dashboard is insufficient, while replacing the application with a full third-party video editor would unnecessarily rewrite validated business logic.

The recommended source of reusable editor patterns is [AIEraDev/Clypra](https://github.com/AIEraDev/Clypra). It has the closest functional vocabulary—media browser, timeline, clip controls, captions, transitions, progress indicators and desktop-resizable panels—under MIT, React 19 and TypeScript. Its Tauri/Rust engine must not be imported. Only presentation components and interaction patterns should be adapted into the existing Electron/Vite renderer.

The current backend boundaries remain authoritative:

```text
React presentation
  -> validated Electron IPC or loopback FastAPI
    -> existing TypeScript/Python coordinators
      -> SQLite/project JSON/filesystem/FFmpeg/local model services
```

## 2. Current application analysis

### 2.1 Technology

| Area | Current implementation |
|---|---|
| Desktop shell | Electron 43, Windows custom title bar |
| Frontend | React 19, TypeScript, Vite 8, Zustand |
| UI | CSS design tokens, dark navy/teal compact editor language |
| Desktop backend | TypeScript main process with allowlisted validated IPC |
| AI video backend | Python 3.11+, FastAPI, Pydantic coordinators |
| Persistence | SQLite for desktop jobs/settings; atomic JSON and media files for NewsVid projects |
| Media | FFmpeg/FFprobe, yt-dlp, Playwright/Chromium, GSAP |
| Local AI | Ollama, Piper or F5-TTS, WhisperX, optional ComfyUI |
| Build | pnpm, TypeScript, Vite, PyInstaller |
| Packaging | electron-builder NSIS plus packaged Python backend/tools |
| Target | Windows desktop; renderer remains resizable |
| Tests | Vitest, pytest, Playwright-based UI audit, real-media integration tests |

There is no user authentication workflow. External integrations are local services and public media/article retrieval. Network/process/filesystem access is owned by the Electron main process or Python backend, not the renderer.

### 2.2 Code structure and ownership

| Layer | Important paths | Responsibility |
|---|---|---|
| Electron entry | `src/main/index.ts` | window lifecycle, backend lifecycle, IPC registration |
| Desktop services | `src/main/` | extraction, download queue, storage, diagnostics, updater, FFmpeg composition |
| IPC contracts | `src/shared/contracts.ts`, `src/shared/ipc.ts` | Zod input/output contracts and allowlisted channels |
| Desktop renderer | `src/renderer/App.tsx` | top-level workspaces, drawers and presentation state |
| Downloader UI | `download-composer.tsx`, `job-queue.tsx` | inspect, choose variant, enqueue, monitor and recover |
| Composer UI | `composition-builder.tsx` | clips, trim, speed, audio, multi-logo and output |
| News Studio UI | `web-studio.tsx` | project pipeline, scene editor, preview, QA, models and services |
| News API | `packages/pipeline/src/newsvid/api.py` | projects, resources, jobs, models and workflow operations |
| News orchestration | `packages/pipeline/src/newsvid/*` | deterministic stage coordinators and preflight |
| AI/domain models | `packages/brain/src/newsvid_brain/` | strict facts/script/storyboard/render schemas and providers |
| Ingestion | `packages/article_ingest/src/newsvid_ingest/` | guarded fetch, extraction and image manifest |
| Configuration | `config/app.yaml`, `.service-settings.json`, Electron settings | services, models, paths and user preferences |
| Tests | `tests/` | contracts, lifecycle, queue, composition, pipeline and UI evidence |

### 2.3 Complete feature inventory

| ID | Function | Module/interface | Input | Output | State model | Frequency |
|---|---|---|---|---|---|---|
| F01 | Inspect media URL | extraction adapters | HTTP(S) URL | normalized variants/subtitles | transient result/error | Very high |
| F02 | Single download | job manager | URL + selected variant | validated media artifact | queued through completed/failed | Very high |
| F03 | Batch download | renderer + job manager | multiple URLs | independent jobs | per-item recovery | High |
| F04 | Persistent queue | SQLite/job manager | jobs/priorities | resumable queue | pause/retry/cancel/restart | Very high |
| F05 | Search/filter history | job queue | query/status | matching downloads | persisted UI filter | Medium |
| F06 | Tool discovery/setup | tools/updater | local environment | yt-dlp/FFmpeg status | ready/missing/version | Medium |
| F07 | Diagnostics export | diagnostics | safe filename | diagnostic bundle | success/failure | Low |
| F08 | App update | updater | signed manifest | staged update | configured/available/error | Low |
| F09 | Import video clips | composition builder | up to 20 local videos | ordered clip list | editable | High |
| F10 | Trim and speed | composition spec | start/end/speed | edited segments | strict validation | High |
| F11 | Add/replace audio | composition spec | audio + volume | muxed audio | optional | Medium |
| F12 | Multi-logo overlay | composition spec | up to 8 logos | static/bounce/motion overlays | validated | Medium |
| F13 | Logo styling/timing | composition UI | position/size/colors/timeline | overlay configuration | editable | Medium |
| F14 | Composition rendering | FFmpeg coordinator | composition spec | validated final artifact | queued/processing/failed/completed | High |
| F15 | Create News project | FastAPI/project manager | name | project/checkpoint | persistent | High |
| F16 | Ingest article | ingestion coordinator | URL or local file | article/source/images | cached/fingerprinted | High |
| F17 | Extract grounded facts | FactsCoordinator/Ollama | article | `facts.json` | validated/retry/fallback | High |
| F18 | Generate news script | ScriptCoordinator/Ollama | facts/style/duration | `script.json` | validated/fact-linked | High |
| F19 | Build storyboard | StoryboardCoordinator | script/facts/images | `storyboard.json` | editing source of truth | High |
| F20 | Edit scenes | News Studio API | narration/facts/visual/template | updated storyboard | invalidates affected cache | High |
| F21 | Generate narration | Piper/F5-TTS | scene narration/voice | WAV + manifest | per-scene cache | High |
| F22 | Align captions | WhisperX | WAV/transcript | words + ASS | cached/validated | High |
| F23 | Generate AI visual | ComfyUI | routed generated scene | image manifest/assets | optional/resumable | Medium |
| F24 | Render one scene | Chromium/GSAP/FFmpeg | storyboard scene | scene MP4 | selective cache | High |
| F25 | Quick preview | video renderer | valid scenes/audio | caption-free MP4 | resumable | High |
| F26 | Captioned preview | alignment + renderer | scenes/audio/ASS | preview MP4 | resumable | Very high |
| F27 | Final render | final assembler | validated preview | final MP4 + manifest | cached/validated | High |
| F28 | Quality assurance | QA coordinator | latest project assets/output | readable check report | pass/fail/not-run | High |
| F29 | Dependency preflight | doctor engine | target operation | dependency report/autofix | ready/fixable/blocked | High |
| F30 | Model selection | settings/model discovery | live local services | saved provider/model choices | ready/offline | Medium |
| F31 | Background progress | Electron subscriptions/FastAPI jobs | running job | stage/progress/message/error | live | Very high |
| F32 | Project/job history | SQLite/project JSON | completed work | inspectable history/output | persistent | Medium |

Core: F01–F04, F09–F28, F31. Secondary: F05, F32. Configuration: F06, F30. Monitoring/recovery: F28, F29, F31. Maintenance: F07, F08. Advanced: detailed logo motion, manual scene templates and optional ComfyUI.

## 3. User workflow analysis

### 3.1 Download workflow

```text
Download workspace -> paste URL(s) -> inspect -> choose variant -> enqueue
-> live queue -> validate artifact -> open output or retry
```

Happy path: two to three primary actions. Batch mode repeats inspection automatically.
Error path: invalid URL, unsupported/protected media, extractor/network timeout, tool missing, invalid output.
Recovery: edit URL, enable an explicitly allowed fallback, retry a failed job, cancel, or inspect diagnostics. One failed job does not stop the queue.

### 3.2 Composition workflow

```text
Composer -> select clips -> reorder/trim/speed -> optional audio/logos
-> choose output -> render -> progress -> validated artifact
```

Error path: missing or duplicated file, invalid trim interval, conflicting input roles, FFmpeg capability/error.
Recovery: correct only the invalid control, retry composition, preserve the composition spec and unaffected files.

### 3.3 AI News happy path

```text
Projects -> create/open -> supply article -> Create complete video
-> facts -> script -> storyboard -> TTS -> captions -> visuals as required
-> scenes -> captioned preview -> validation -> final output
```

The frequent path should be one launch action plus optional review, not eleven manual tabs. Existing valid stage fingerprints must be reused.

### 3.4 AI News review/edit path

```text
Open project -> Storyboard/editor -> select scene -> edit narration/facts/visual
-> save -> regenerate only affected audio/visual/scene -> preview -> QA
```

### 3.5 AI News error and recovery path

| Failure | UX response | Recovery action |
|---|---|---|
| Ungrounded fact/script reference | show scene/fact and evidence issue | regenerate affected stage or edit reference |
| Ollama/model unavailable | dependency card with actual model status | automatic setup/pull, then resume pending operation |
| Piper voice unavailable | download progress and checksum status | automatic trusted voice setup |
| WhisperX unavailable | show caption dependency only when needed | automatic isolated setup/start or quick preview |
| ComfyUI unavailable | block only a scene that actually requires it | start service/change checkpoint/change visual route |
| Renderer/tool failure | stage, safe command context and affected scene | retry scene, then continue workflow |
| Missing final manifest after preview | mark final as not run, validate preview | render final directly from QA |
| App restart | reconcile checkpoint/artifacts | resume from last valid boundary |

## 4. UI complexity and priority

| Capability | Complexity | Frequency | Importance | Priority |
|---|---|---|---|---|
| Paste/inspect/download | Medium | Very high | Critical | P1 |
| Active jobs/progress | High | Very high | Critical | P1 |
| Create complete AI video | High internally, low interaction | High | Critical | P1 |
| Preview/video result | Medium | Very high | Critical | P1 |
| Clip/scene editor | High | High | Important | P1 |
| Project browser/recent work | Medium | High | Important | P2 |
| QA and recovery | Medium | High | Critical | P2 |
| History/search/filter | Medium | Medium | Important | P2 |
| Model/voice selection | Medium | Medium | Important | P3 |
| Dependencies/services | High | Low until failure | Important | P3, surfaced contextually |
| Diagnostics/updater/retention | Low | Low | Secondary | P4 |
| Advanced FFmpeg/logo/model parameters | High | Low | Secondary | P4 |

## 5. Information architecture

```text
APPLICATION
├─ Home / Recent work
│  ├─ Resume project
│  ├─ Active tasks
│  └─ Recent outputs
├─ Download
│  ├─ Inspect / single / batch
│  └─ Queue
├─ Compose
│  ├─ Media bin
│  ├─ Preview canvas
│  ├─ Timeline
│  └─ Properties
├─ AI News
│  ├─ Project overview + one-click workflow
│  ├─ Article and grounded content
│  ├─ Storyboard / scene editor
│  ├─ Preview and final output
│  └─ QA
├─ Activity
│  ├─ Running
│  ├─ Needs attention
│  └─ History
└─ Settings
   ├─ Output/download behavior
   ├─ Models and voices
   ├─ Services and dependencies
   └─ Advanced / diagnostics / updates
```

This reduces the News Studio's internal stage navigation. Facts, script and technical artifacts remain inspectable inside project detail, but the default project page leads with next action, progress and output.

## 6. UX requirements

- One persistent activity button must aggregate desktop and NewsVid jobs.
- One primary action per context: Download, Render composition, or Create complete video.
- Stage details use progressive disclosure; service screens are not normal workflow steps.
- Model controls are discovered selects with readiness and resource-cost labels, never unvalidated text fields.
- Errors must identify the failed object and offer Retry, Resume, Edit, Skip when safe, or View details.
- Cancelling must be distinct from closing a panel.
- Completed and cached stages must be visible so reuse is predictable.
- Empty states explain the next action; loading states retain layout; success states expose the output.
- Keyboard focus, 32 px minimum targets, tab semantics and reduced motion remain mandatory.
- At 1280x720, the primary action, current result and active failure must remain reachable without horizontal page overflow.

## 7. Required UI components

| Group | Required components |
|---|---|
| Shell | compact sidebar/workspace switcher, title bar, activity drawer, command search |
| Project | project cards/list, recent output, stage stepper, next-action banner |
| Editing | media bin, resizable preview, scene/clip list, timeline, properties inspector |
| Data | searchable/filterable job list, status badges, resource/model selects |
| Actions | primary action, contextual menu, retry/resume/cancel, confirmation dialog |
| Monitoring | aggregate progress, per-stage progress, activity feed, expandable technical details |
| Configuration | select, segmented provider control, accordion for advanced options, dependency card |
| Feedback | toast, inline validation, actionable error state, empty/loading/success state |

A statistics-heavy dashboard, authentication pages, CRUD pagination and generic business charts are not core requirements.

## 8. GitHub repository search strategy

Queries were derived from real functions: React desktop video editor timeline, local AI workflow desktop, automation job progress, media sidebar/properties panel, React Vite accessible sidebar and task history. Candidates were then checked through repository source trees, package manifests and license files rather than screenshots alone.

Snapshot metadata below was refreshed on 2026-08-29 through GitHub repository metadata.

## 9. Repository candidates

### 9.1 AIEraDev/Clypra

- URL: https://github.com/AIEraDev/Clypra
- Snapshot: 3,152 stars; 311 forks; pushed 2026-08-28; MIT.
- Technology: React 19, TypeScript, Vite, Zustand, Radix/shadcn, Tauri/Rust.
- Source evidence: explicit `editor/sidebar`, `editor/timeline`, captions, transitions, media-job indicator, dialogs and property sections.
- UI style: professional desktop editor with media/property/timeline regions.
- Reusable: layout, sidebar tabs, timeline ruler/toolbar, clip context menu, empty timeline state, media progress, toast/dialog patterns.
- Dark/theme: editor-oriented dark UI; reusable styling system.
- Documentation/testing: extensive README, strict TypeScript, Vitest and component tests.
- Integration difficulty: Medium. Presentation patterns fit strongly; Tauri commands and proprietary engine calls must be replaced by existing IPC/FastAPI adapters.

### 9.2 OpenCut-app/OpenCut

- URL: https://github.com/OpenCut-app/OpenCut
- Snapshot: 87,869 stars; 8,666 forks; pushed 2026-08-10; MIT.
- Technology: TypeScript/React, TanStack Start/Router, Base UI/Radix, shadcn, resizable panels, Zod.
- UI style: cross-platform creator/video editor.
- Reusable: resizable editor shell, command menu, dialogs, forms, theme primitives and future plugin-oriented editor concepts.
- Dark/theme: yes through `next-themes`; strong modern component set.
- Documentation: visible roadmap and active releases, but the main project is explicitly being rewritten and recommends classic for current use.
- Integration difficulty: Medium-high. Excellent vocabulary but architecture is in transition and TanStack Start/server assumptions are unnecessary in Electron.

### 9.3 contextui-desktop/contextui

- URL: https://github.com/contextui-desktop/contextui
- Snapshot: 22 stars; 3 forks; pushed 2026-03-04; Apache-2.0.
- Technology: Electron, React, Vite, TypeScript, flexible panel layout, Python environment manager.
- UI style: local AI workflow browser with draggable tabs.
- Reusable: workflow cards/browser, tab manager, Python service lifecycle presentation, module status and local-first mental model.
- Dark/theme: workflow-centric desktop appearance; less mature component system.
- Documentation: architecture/build/workflow docs are unusually detailed for its size.
- Integration difficulty: Medium. Conceptual match is strong, but only 19 commits and its documented `nodeIntegration=true`, `contextIsolation=false` security model must not be copied.

### 9.4 satnaing/shadcn-admin

- URL: https://github.com/satnaing/shadcn-admin
- Snapshot: 14,059 stars; 2,163 forks; pushed 2026-07-21; MIT.
- Technology: React, TypeScript, Vite, TanStack Query/Router/Table, Zustand, Radix/shadcn.
- UI style: accessible responsive admin shell.
- Reusable: sidebar, command search, sheets/dialogs, data table, settings layout, badges, forms and light/dark theme.
- Dark/theme: built in; responsive and accessibility are stated goals.
- Documentation: good source organization and active tagged releases.
- Integration difficulty: Low-medium at component level. Functional fit is weaker: no media timeline, preview canvas or creator workflow.

### 9.5 marmelab/react-admin

- URL: https://github.com/marmelab/react-admin
- Snapshot: 26,913 stars; 5,467 forks; pushed 2026-08-27; MIT.
- Technology: React/TypeScript framework over REST/GraphQL, Material UI, headless `ra-core` packages.
- UI style: mature data/CRUD administration.
- Reusable: lists, filters, forms, notifications, optimistic state, offline/data provider patterns.
- Dark/theme: Material theme support; broad forms/tables/dialog coverage.
- Documentation: strongest of the candidates, active mature monorepo.
- Integration difficulty: Medium-high. Its resource/data-provider abstraction would wrap or reshape current bespoke IPC and workflow APIs without solving editor interaction.

## 10. Repository scoring and comparison

### 10.1 Weighted score

| Candidate | Functional 25 | Workflow 20 | UX 15 | Integration 15 | UI 10 | Arch. 5 | Docs 5 | License 5 | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Clypra | 24 | 18 | 13 | 12 | 9 | 4 | 4 | 5 | **89** |
| OpenCut | 23 | 18 | 13 | 10 | 10 | 4 | 3 | 5 | **86** |
| ContextUI | 20 | 19 | 12 | 10 | 7 | 3 | 4 | 5 | **80** |
| shadcn-admin | 15 | 13 | 14 | 15 | 9 | 4 | 4 | 5 | **79** |
| react-admin | 13 | 12 | 13 | 9 | 8 | 5 | 5 | 5 | **70** |

### 10.2 Top-three comparison

| Criterion | Clypra | OpenCut | ContextUI |
|---|---:|---:|---:|
| Functional fit | Excellent editor primitives | Excellent creator primitives | Excellent AI workflow concepts |
| UX fit | Timeline + media + properties | Creator-first and polished | Workflow browser + draggable tabs |
| Integration | Adapt React components; replace Tauri calls | Untangle changing TanStack architecture | Adapt concepts; reject unsafe Electron boundary |
| Maintainability | Feature-based component tree | Rewrite increases churn risk | Small and immature |
| UI quality | High | Very high | Medium-high |
| License | MIT | MIT | Apache-2.0 |
| Migration effort | Medium | Medium-high | Medium |
| Main risk | accidentally importing engine coupling | upstream rewrite/API churn | security model and low maturity |

**Best match: Clypra**, as a component and interaction reference—not as a replacement runtime.

## 11. Final recommendation

Adopt a Clypra-inspired editor workspace inside the current shell:

- left rail: workspace and project/media navigation;
- center: preview/result canvas;
- bottom: timeline or stage strip depending on workspace;
- right: context properties and model choices;
- global activity drawer: all active/download/composition/NewsVid jobs;
- project overview: one-click workflow and next required action.

Use the current navy/teal tokens, Vietnamese localization and accessibility rules. Do not visually clone branding or import its Tauri/Rust engine.

## 12. Function-to-UI mapping

| Existing function | UI location | Component | User action |
|---|---|---|---|
| Inspect/download | Download workspace | source command bar + variant sheet | paste, inspect, download |
| Batch download | Download workspace | batch mode panel | paste list, enqueue |
| Active queue | global activity drawer | compact task cards | monitor/retry/cancel |
| History | Activity | searchable job table | inspect/open output |
| Compose media | Compose | media bin + canvas + timeline | add/reorder/trim |
| Audio/logos | Compose properties | collapsible inspector | configure/preview |
| Composition render | Compose header | primary render action | render and monitor |
| News projects | AI News home | recent project cards | create/resume |
| Article/facts/script | Project content drawer | stage artifact viewer | inspect/regenerate |
| Storyboard scenes | AI News editor | scene list/timeline | select/reorder/edit |
| Narration/voice | scene properties/settings | discovered select + regenerate | choose/listen/apply |
| Captions | preview/editor | caption track and style panel | preview/regenerate |
| Visual generation | scene properties | source route/model card | generate/change source |
| Preview | center canvas | video player + version state | review |
| QA | project result | readable checklist | fix or render final |
| Models | settings | discovered model cards/selects | choose and save |
| Dependencies | contextual error + settings | readiness card | auto-fix/view details |
| Diagnostics/update | advanced settings | maintenance cards | export/check update |

## 13. Proposed UI architecture

```text
src/renderer
├─ shell
│  ├─ WorkspaceRail
│  ├─ CommandBar
│  └─ ActivityDrawer
├─ workspaces
│  ├─ download
│  ├─ compose
│  └─ news
├─ editor
│  ├─ MediaBin
│  ├─ PreviewCanvas
│  ├─ TimelineOrStages
│  └─ PropertiesInspector
├─ components
│  ├─ status / progress / error / empty
│  ├─ dialogs / selects / sheets
│  └─ resizable-panels
├─ adapters
│  ├─ electron-ipc.ts
│  └─ newsvid-api.ts
├─ state
│  ├─ ui-store.ts
│  └─ normalized-job-view.ts
└─ locales/vi.json
        ↓
existing IPC + FastAPI contracts
        ↓
existing TypeScript and Python business logic
```

Adapt from Clypra: editor region layout, sidebar tab mechanics, timeline ruler/toolbar interaction, clip/scene context menu, property-section grouping, media-job indicator and empty timeline pattern.

Write locally: unified task normalization, NewsVid stage strip, project overview, grounded-fact presentation, service/model readiness and QA recovery cards.

Keep unchanged: Electron IPC contracts, SQLite/job manager, FFmpeg composition, FastAPI routes, Python coordinators, schemas, checkpoints and artifacts.

State policy: Zustand holds local presentation state; server-owned jobs/projects remain fetched/subscribed state. Do not duplicate pipeline truth in a new client store.

## 14. Migration strategy

1. Freeze API/IPC contracts with existing tests and add UI adapter contract tests.
2. Introduce shared tokens and primitive components without changing page structure.
3. Add the global activity drawer adapter that normalizes both job systems.
4. Convert shell navigation to workspace rail while preserving current tab keyboard behavior.
5. Migrate Compose into media/canvas/timeline/properties regions behind the same handlers.
6. Migrate AI News project overview and collapse manual stages into inspectable detail.
7. Add contextual error recovery and model/service selects.
8. Run feature-by-feature parity, UI audit and real media acceptance before removing old components.

Use a strangler migration: old and new presentations can coexist behind a development flag until parity is proven. No big-bang replacement.

## 15. Implementation plan

| Increment | Deliverable | Acceptance |
|---|---|---|
| 1 | design tokens, primitive buttons/cards/selects/dialogs | UI score at target, keyboard/focus preserved |
| 2 | workspace rail + command bar + activity drawer | all four current top-level routes and jobs reachable |
| 3 | normalized job view | retry/cancel/progress/history parity for both engines |
| 4 | Compose editor layout | all clip/audio/logo/timing fields preserved |
| 5 | AI News project overview | full render in one action; stages inspectable |
| 6 | scene editor layout | save/selective regeneration/cache behavior preserved |
| 7 | models/services/QA recovery | no manual model text; actionable dependency errors |
| 8 | responsive/accessibility hardening | 1280x720, resize, keyboard, reduced motion pass |
| 9 | package and real-media validation | typecheck/tests/build/backend/package/lifecycle smoke pass |

## 16. Technical risks

- Framework mismatch: never bring Tauri/Rust commands from Clypra into Electron.
- Dependency growth: copy only necessary patterns; prefer current CSS/components before adding Radix packages.
- Timeline divergence: current composition timeline and News storyboard are different domain models; share visuals, not data models.
- Dual async systems: normalize display only; do not merge Electron and FastAPI job persistence.
- Renderer security: retain context isolation and allowlisted IPC; explicitly reject ContextUI's privileged renderer pattern.
- Packaging: every new asset/dependency must be verified in NSIS and packaged backend mode.
- Upstream drift: vendor no live dependency on candidate repositories; record license/source mapping for adapted code.

## 17. UX risks

- A creator-style timeline can intimidate users whose goal is one-click generation. Default to project overview; editor is a deliberate second level.
- Hiding stages too deeply can impede debugging. Keep an expandable stage inspector and activity details.
- One global progress number can conceal the failing job. Always show the item needing attention first.
- Too many model choices invite poor hardware combinations. Label recommended/installed/resource cost and default safely.
- A dashboard full of charts wastes primary space. Use recent work, active failures and outputs instead.
- Resize layouts can create inaccessible controls. Define minimum panel widths and collapse low-priority inspectors.

## 18. Final verdict

### Five required answers

1. **What does the application do?** It downloads and validates media, composes clips/audio/logos, and produces grounded Vietnamese news videos through a resumable local AI/media pipeline.
2. **How is it used?** Three primary workspace workflows share background task monitoring, history, settings and recovery.
3. **Which UI architecture fits?** A hybrid desktop media workspace plus automation control panel with progressive project detail.
4. **Which repository fits best?** Clypra, because its editor interaction primitives match actual frequent work while React/TypeScript components can be adapted under MIT.
5. **How can it be integrated safely?** Adapt only presentation components through existing IPC/FastAPI adapters, migrate incrementally, and retain every business/data/render boundary.

```text
RECOMMENDED REPOSITORY:
https://github.com/AIEraDev/Clypra

RECOMMENDED UI ARCHITECTURE:
Hybrid desktop media workspace + automation control panel, with project overview as the default and editor regions disclosed on demand.

WHY THIS REPOSITORY:
It has the strongest functional and workflow match: media bin, preview canvas, timeline, captions, transitions, properties, job indicators and desktop interaction patterns. Its MIT React/TypeScript presentation can be adapted while excluding its Tauri/Rust engine.

INTEGRATION DIFFICULTY:
MEDIUM

ESTIMATED MIGRATION SCOPE:
Incremental renderer-shell and component migration across navigation, activity, Compose and AI News; no backend, data model or render-engine rewrite.

FUNCTIONALITY PRESERVATION:
All actions continue through existing validated Electron IPC and FastAPI endpoints. Current SQLite, project files, checkpoints, providers, FFmpeg and background job engines remain authoritative.

NEXT STEP:
Build a development-only shell prototype for Home, Compose and AI News project overview using current data adapters, then run feature parity, keyboard, resize, UI audit and real-media tests before enabling it by default.
```
