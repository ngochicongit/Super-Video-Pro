# MASTER_PLAN.md

# AI NEWS VIDEO — LOCAL WINDOWS

## URL → Vietnamese AI News Video → 1080×1920 MP4

Version: 2.0 — Reuse-First Architecture

---

# 0. PROJECT OBJECTIVE

Build a production-grade local AI News Video system for Windows.

Primary workflow:

URL
→ Article Extraction
→ Source Metadata
→ Fact Extraction
→ Vietnamese Script
→ Storyboard
→ Vietnamese TTS
→ Word Alignment
→ Subtitles
→ Visual Planning
→ Article Assets / Charts / AI Images
→ Motion Graphics
→ Scene Rendering
→ Preview
→ Automated QA
→ Selective Fix
→ Final 1080×1920 MP4

The system must be designed for:

* local execution;
* Windows 10/11;
* consumer NVIDIA GPUs where available;
* modular AI services;
* resumable generation;
* deterministic caching;
* selective scene regeneration;
* Codex/Cursor autonomous editing;
* Vietnamese news content;
* vertical TikTok / Shorts / Reels video.

---

# 1. PRIMARY IMPLEMENTATION STRATEGY

This project MUST NOT be unnecessarily rewritten from scratch.

Mandatory engineering strategy:

REUSE
↓
ADAPT
↓
EXTEND
↓
WRITE NEW

Definitions:

REUSE
Existing upstream implementation works with minimal modification.

ADAPT
Existing implementation is useful but must be integrated into our architecture.

EXTEND
Existing implementation provides the foundation but requires new functionality.

WRITE_NEW
No suitable upstream implementation exists.

WRITE_NEW IS THE LAST OPTION.

Before implementing any subsystem, Codex MUST search upstream source code.

If WRITE_NEW is selected, document:

WHY_EXISTING_CODE_CANNOT_BE_REUSED

No subsystem may be rewritten simply because writing new code appears easier.

---

# 2. UPSTREAM REPOSITORIES

Create:

.upstream/

Clone:

https://github.com/Juwebien/videogen
→ .upstream/videogen

https://github.com/hoquanghai/Auto-Create-Video
→ .upstream/auto-create-video

https://github.com/nexu-io/html-video
→ .upstream/html-video

https://github.com/sausheong/newsvid
→ .upstream/newsvid

Add:

.upstream/

to `.gitignore`.

Upstream repositories are READ-ONLY references.

Never modify upstream repositories.

The main project must not depend at runtime on `.upstream/`.

---

# 3. UPSTREAM RESPONSIBILITIES

## 3.1 VIDEOGEN

Primary source for media pipeline infrastructure.

Priority areas:

pipeline orchestration
checkpoint/resume
cache
project processing
local LLM
TTS architecture
STT/alignment
word timestamps
ASS subtitles
karaoke subtitles
image handling
Ken Burns
ComfyUI
FFmpeg
xfade transitions
vertical rendering
error handling
tests

Reuse priority:

VERY HIGH

---

# 3.2 AUTO-CREATE-VIDEO

Primary source for Vietnamese social/news motion design.

Priority areas:

Vietnamese article → video workflow
vertical 9:16 composition
HyperFrames
GSAP
motion graphics
hook scenes
stat scenes
comparison
timeline
charts
feature lists
kinetic typography
scene timing
transitions
typography
design system

Reuse priority:

HIGH

---

# 3.3 HTML-VIDEO

Primary source for agent-driven rendering infrastructure.

Priority areas:

Codex CLI integration
Cursor Agent integration
agent discovery
agent execution
content graph
storyboard-like intermediate representation
multi-frame video architecture
template metadata
template discovery
template provenance
HyperFrames renderer
Chromium capture
FFmpeg export
per-frame rendering
Studio architecture
agent iteration
render/inspect/edit loop

Reuse priority:

VERY HIGH

---

# 3.4 NEWSVID

Secondary reference.

Priority areas:

simple news pipeline
URL processing
Ollama
TTS orchestration
stock media
FFmpeg composition

Reuse priority:

LOW / MEDIUM

Use when implementation is simpler or superior for a specific subsystem.

---

# 4. LICENSE AND PROVENANCE

Upstream code may only be reused when its license permits the intended use.

Create:

THIRD_PARTY_NOTICES.md

Create:

licenses/upstream/

Create:

docs/UPSTREAM_REUSE_AUDIT.md

Create:

docs/UPSTREAM_SOURCE_MAP.md

For every copied/adapted component record:

repository
source file
license
destination
reuse type
modifications

Example:

Repository:
Juwebien/videogen

Source: <actual source path>

License:
MIT

Reuse:
ADAPT

Destination:
packages/renderer/

Changes:
Adapted to project-based storyboard architecture and selective rerendering.

Never remove required copyright notices.

Never copy code with unclear licensing.

---

# 5. REUSE AUDIT

Before each phase Codex MUST inspect actual source files.

README inspection alone is insufficient.

Classification:

DIRECT_REUSE
ADAPT
EXTEND
REFERENCE_ONLY
WRITE_NEW

Maintain:

docs/UPSTREAM_REUSE_AUDIT.md

Table:

| Subsystem | Repository | Source | License | Strategy | Destination | Reason |

Maintain:

docs/UPSTREAM_SOURCE_MAP.md

This document maps upstream modules to our architecture.

---

# 6. ARCHITECTURAL RULE

Upstream code must conform to OUR interfaces.

Never allow upstream-specific models to spread through the entire application.

Pattern:

UPSTREAM
↓
ADAPTER
↓
OUR INTERFACE
↓
PIPELINE

Example:

Videogen ComfyUI
↓
adapter
↓
ComfyUIProvider
↓
VisualPipeline

Another:

html-video renderer
↓
adapter
↓
HTMLRenderer
↓
SceneRenderer

---

# 7. TARGET REPOSITORY

ai-news-video/
│
├── apps/
│   ├── studio/
│   │   ├── frontend/
│   │   └── backend/
│   └── desktop/
│
├── packages/
│   ├── article_ingest/
│   ├── brain/
│   ├── tts/
│   ├── subtitles/
│   ├── visual/
│   ├── renderer/
│   ├── templates/
│   ├── pipeline/
│   └── agents/
│
├── services/
│   ├── ollama/
│   ├── comfyui/
│   ├── f5tts/
│   └── whisper/
│
├── workflows/
│   ├── comfyui/
│   └── video/
│
├── tools/
│
├── config/
│
├── projects/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── docs/
│
├── licenses/
│
├── .agents/
│
├── MASTER_PLAN.md
├── AGENTS.md
├── ARCHITECTURE.md
├── THIRD_PARTY_NOTICES.md
├── README.md
├── ROADMAP.md
├── pyproject.toml
├── package.json
├── docker-compose.yml
├── .env.example
└── .gitignore

Do NOT create placeholder implementations for future phases.

Create files when they become necessary.

---

# 8. WINDOWS ENVIRONMENT

Primary:

Windows 10/11

Required:

Git
Python 3.11
Node.js LTS
FFmpeg
Ollama

Optional:

NVIDIA CUDA
WSL2
Docker Desktop

Architecture:

Windows
│
├── Python
│   └── core pipeline
│
├── Node
│   └── HTML renderer
│
├── Ollama
│   └── LLM
│
├── ComfyUI Portable
│   └── visual generation
│
├── FFmpeg
│
└── WSL2 / isolated environment
└── F5-TTS

Do not put all AI dependencies into one environment.

---

# 9. PROJECT DATA MODEL

Every video is an independent project.

projects/<project_id>/
│
├── project.json
├── source.json
├── article.md
├── images.json
├── facts.json
├── script.json
├── storyboard.json
│
├── audio/
├── images/
├── clips/
├── captions/
├── scenes/
├── cache/
├── logs/
│
└── output/
├── preview.mp4
└── final.mp4

The editing source of truth is:

storyboard.json

Never manually edit generated binary assets as the primary editing workflow.

---

# 10. PIPELINE

Pipeline stages:

INGEST
↓
FACTS
↓
SCRIPT
↓
STORYBOARD
↓
TTS
↓
ALIGNMENT
↓
VISUALS
↓
SCENE_RENDER
↓
PREVIEW
↓
QA
↓
FINAL_RENDER

Every stage must support:

status
cache
checkpoint
error reporting
resume

---

# 11. ARTICLE INGESTION

Target:

URL
→ article.md
→ source.json
→ images.json

Preferred strategy:

reuse/adapt upstream source handling

plus when required:

Trafilatura
→ Playwright fallback
→ DOM heuristics

source.json:

{
"url": "",
"domain": "",
"title": "",
"author": "",
"published_at": "",
"language": "",
"hero_image": "",
"retrieved_at": ""
}

images.json must retain source URLs and attribution metadata.

Treat scraped HTML as untrusted.

Never execute arbitrary article JavaScript in our renderer.

---

# 12. FACT GROUNDING

This component is expected to require significant new product-specific logic.

ARTICLE MUST NOT GO DIRECTLY TO FINAL SCRIPT.

Pipeline:

article.md
↓
FACT EXTRACTION
↓
facts.json
↓
SCRIPT

facts.json:

{
"source": {
"url": "",
"publisher": "",
"title": ""
},

"facts": [
{
"id": "fact_001",
"claim": "",
"evidence": "",
"importance": 0.0,
"confidence": 0.0
}
]
}

Never invent:

numbers
dates
quotes
people
events
claims

Preserve uncertainty.

---

# 13. LLM ARCHITECTURE

Default:

Ollama + Qwen

Interface:

LLMProvider

Business logic must not depend directly on Ollama.

Initial implementation:

OllamaProvider

Future:

OpenAI-compatible
LM Studio
llama.cpp
vLLM

Reuse Videogen/newsvid local LLM code where technically suitable.

---

# 14. SCRIPT

facts.json
↓
script.json

Default:

Vietnamese
60 seconds

Supported:

30–90 seconds

Styles:

breaking-news
tech-news
finance-news
explainer
documentary

Every factual narration segment MUST contain:

fact_refs

No unresolved fact reference is allowed.

---

# 15. STORYBOARD

storyboard.json is the editing source of truth.

Example:

{
"video": {
"width": 1080,
"height": 1920,
"fps": 30,
"target_duration": 60,
"style": "tech-news"
},

"scenes": [
{
"id": "scene_001",
"type": "hook",
"narration": "",
"fact_refs": ["fact_001"],

```
  "visual": {
    "type": "kinetic_text",
    "template": "breaking_hook",
    "source": null,
    "prompt": null
  }
}
```

]
}

Inspect html-video content graph before implementing this subsystem.

Reuse/adapt its concepts or implementation where suitable.

---

# 16. SCENE TYPES

Minimum:

hook
headline
article-image
kinetic-text
stat-hero
chart
comparison
feature-list
timeline
quote
screenshot
AI-illustration
map
outro

Prioritize reuse from Auto-Create-Video templates.

---

# 17. VISUAL ROUTER

Implement:

VisualRouter

Rules:

REAL PERSON / EVENT
→ article/source image

NUMBER
→ chart/stat

CHRONOLOGY
→ timeline

LOCATION
→ map

HOOK
→ kinetic typography

ABSTRACT CONCEPT
→ AI illustration

SOFTWARE / WEBSITE
→ screenshot where appropriate

Never default every scene to AI-generated imagery.

---

# 18. VISUAL PROVENANCE

Every visual must have:

source_type

Possible values:

article
generated
stock
user
graphic
screenshot

Example:

{
"source_type": "article",
"source_url": "",
"local_path": ""
}

AI:

{
"source_type": "generated",
"generator": "comfyui",
"workflow": "news-image"
}

---

# 19. TTS

Interface:

TTSProvider

Providers:

FAST
→ Piper

QUALITY
→ F5-TTS Vietnamese

F5-TTS runs as isolated local service.

Reuse/adapt upstream TTS/cache infrastructure.

---

# 20. VIETNAMESE NORMALIZATION

Implement:

normalize_vi.py

External dictionary:

config/pronunciation_vi.yaml

Handle:

numbers
years
percentages
currency
dates
units
technology abbreviations

Example:

AI → ây ai
GPU → gi pi diu
CEO → si i ô
USD → đô la Mỹ

Do not hardcode the entire dictionary into application logic.

---

# 21. AUDIO CACHE

Per scene:

audio/scene_001.wav

Fingerprint:

narration
voice
provider
provider configuration

Unchanged narration must not regenerate TTS.

---

# 22. ALIGNMENT

Pipeline:

WAV
↓
WhisperX / alignment provider
↓
word timestamps

Output:

captions/scene_001.words.json

Prefer reuse from Videogen where available.

---

# 23. SUBTITLES

Reuse/adapt Videogen subtitle implementation where suitable.

Output:

ASS

Support:

word timing
active word highlight
karaoke
adaptive layout
safe areas
TikTok-style captions

Default safe areas:

top: 180px
bottom: 300px

Prefer:

≤ approximately 7 words per caption line.

---

# 24. STATIC VISUALS

First complete renderer MUST work without ComfyUI.

Pipeline:

article imagery
+
Ken Burns
+
crop
+
pan/zoom
+
captions
+
voice
+
FFmpeg

→ vertical MP4

Reuse Videogen heavily.

---

# 25. MOTION GRAPHICS

Primary upstreams:

Auto-Create-Video
html-video

Use:

HyperFrames
HTML
CSS
Canvas where useful
GSAP
Chromium

Motion scenes:

hook
headline
statistics
charts
comparison
timeline
quote
kinetic typography
outro

Prefer html-video for renderer/runtime infrastructure.

Prefer Auto-Create-Video for news/social visual design.

Do not build another browser rendering engine without justification.

---

# 26. COMFYUI

Independent service.

Default:

http://127.0.0.1:8188

Reuse/adapt Videogen ComfyUI implementation.

Interface:

ComfyUIProvider

Functions:

health_check
queue_prompt
wait_for_completion
collect_outputs

Initial workflows:

news-image.json
background.json
infographic.json

ComfyUI is OPTIONAL.

Pipeline must work without it.

---

# 27. ADVANCED AI VIDEO

Not MVP.

Potential later:

Wan
LTX
AnimateDiff
HunyuanVideo

These must remain optional.

MVP visual strategy:

real imagery
+
AI image
+
Ken Burns
+
motion typography
+
charts
+
timeline
+
transitions

---

# 28. RENDERING

Unified architecture:

Visual
+
Motion Graphic
+
Audio
+
Caption
↓
SceneRenderer
↓
RenderedScene
↓
FinalAssembler
↓
FFmpeg
↓
MP4

Target:

1080×1920
30fps
H.264
AAC

Centralize FFmpeg execution.

Reuse/adapt Videogen FFmpeg implementation.

Do not scatter FFmpeg subprocess commands throughout modules.

---

# 29. SELECTIVE REGENERATION

Critical requirement.

If narration changes:

TTS
↓
alignment
↓
captions
↓
scene render

If visual prompt changes:

visual
↓
scene render

If only transition changes:

final assembly

Unrelated scenes remain cached.

Reuse Videogen checkpoint/cache architecture wherever possible.

---

# 30. CHECKPOINT

Stages:

INGEST
FACTS
SCRIPT
STORYBOARD
TTS
ALIGNMENT
VISUALS
SCENES
PREVIEW
QA
FINAL_RENDER

Failure must be resumable.

Command:

newsvid resume PROJECT_ID

---

# 31. CLI

Executable:

newsvid

Required:

newsvid doctor

newsvid ingest URL

newsvid create URL

newsvid resume PROJECT

newsvid inspect PROJECT

newsvid validate PROJECT

newsvid preview PROJECT

newsvid render PROJECT

newsvid render-scene PROJECT SCENE

newsvid regenerate-tts PROJECT SCENE

newsvid regenerate-visual PROJECT SCENE

newsvid qa PROJECT

---

# 32. CREATE OPTIONS

Example:

newsvid create "<URL>" 
--duration 60 
--lang vi 
--style tech-news 
--voice news-male 
--visual hybrid

Visual:

hybrid
article-only
AI-heavy
graphics-heavy

Default:

hybrid

---

# 33. DOCTOR

Check:

Python
Node
FFmpeg
Ollama
configured LLM
Playwright
ComfyUI
Piper
F5-TTS
WhisperX

Optional dependencies must be marked accordingly.

Example:

FFmpeg       OK
Ollama       OK
Qwen         OK
Playwright   OK
ComfyUI      OPTIONAL/OFFLINE
Piper        OK
F5-TTS       OPTIONAL/OFFLINE
WhisperX     OK

---

# 34. QA

Generate:

qa.json

Validate:

facts
fact references
assets
audio
caption overflow
safe areas
scene durations
duplicate visuals
blank scenes
resolution
fps
final duration
FFmpeg errors

Critical failures must produce non-zero CLI exit code.

---

# 35. VIDEO INSPECTION

Implement:

inspect_video

Extract:

duration
resolution
fps
audio metadata
scene boundaries
representative frames
contact sheet

This enables later agent visual inspection.

---

# 36. AGENT ARCHITECTURE

Primary upstream:

html-video

Reuse/adapt:

Codex detection
Cursor detection
agent invocation
content editing workflow
render iteration
frame workflow

Expose deterministic project tools.

Agents should manipulate:

facts.json where authorized
script.json
storyboard.json

Never manually modify generated MP4/WAV/images as primary editing workflow.

---

# 37. AGENT ROLES

Researcher

ScriptWriter

StoryboardDirector

VisualDirector

Editor

QAAgent

Prompts stored under:

.agents/

or:

packages/agents/

---

# 38. AGENT EDITING LOOP

Generate
↓
Validate
↓
Render Preview
↓
Inspect
↓
Modify Storyboard
↓
Render Changed Scenes
↓
Validate
↓
Preview
↓
QA
↓
Final Render

Maximum automatic revision iterations:

3

Never permit infinite agent loops.

---

# 39. AGENTS.md RULE

AGENTS.md must explicitly state:

Source of truth:

projects/<id>/storyboard.json

Do not regenerate unchanged assets.

Do not introduce facts not contained in facts.json.

Every factual scene must reference valid fact IDs.

Prefer:

real media → real events
chart → numbers
timeline → chronology
AI image → abstract concepts
kinetic typography → hook

Preview before final rendering.

Validate after modifications.

---

# 40. FASTAPI

Only after CLI is stable.

FastAPI is an adapter around the SAME pipeline.

Do not duplicate business logic.

Required future API categories:

projects
ingestion
generation
scenes
render
preview
QA
services

---

# 41. WEB STUDIO

Only after core pipeline.

Technology:

React / Next.js
+
FastAPI

Views:

Projects
New Project
Article
Facts
Script
Storyboard
Scene Editor
Preview
QA
Settings
Services

Scene editor:

narration
fact refs
visual type
visual prompt
template
preview

Actions:

regenerate TTS
regenerate visual
render scene
validate
preview

---

# 42. DESKTOP

Future:

Tauri

Do not implement before Web Studio works.

Do not bundle large models into desktop installer.

---

# 43. CONFIG

config/
├── app.yaml
├── models.yaml
├── pronunciation_vi.yaml
├── caption_styles.yaml
└── visual_styles.yaml

Secrets/service overrides:

.env

Never hardcode absolute Windows paths.

---

# 44. SCHEMAS

Use Pydantic for critical data.

Schemas:

Project
Source
ArticleImage
Fact
FactSet
Script
ScriptSegment
Storyboard
Scene
Visual
VisualDecision
AudioAsset
WordTiming
Caption
QAResult
Checkpoint

Validate all stage boundaries.

---

# 45. LOGGING

Structured logs.

Per project:

projects/<id>/logs/

Track:

stage
start
end
duration
model
service
cache hit/miss
errors
FFmpeg status
ComfyUI jobs

Never log secrets.

---

# 46. ERRORS

Typed errors:

ArticleExtractionError
LLMError
SchemaValidationError
TTSError
AlignmentError
VisualGenerationError
RenderError
QAError

Errors must be actionable.

---

# 47. TESTING

Default tests MUST NOT require:

Internet
GPU
ComfyUI
Ollama
F5-TTS

External services must be mockable.

Unit tests:

schemas
normalization
cache
visual router
captions
safe areas
FFmpeg command construction
dependency invalidation

Integration tests:

article fixture
LLM mocked response
TTS mocked/local
alignment
scene render
checkpoint/resume
selective regeneration

Reuse/port useful upstream tests.

---

# 48. LOCAL FIXTURE

Create:

tests/fixtures/article_vi.html

Pipeline must support deterministic local development/testing.

---

# 49. CACHE FINGERPRINTS

FACTS:

article
prompt version
LLM model/config

SCRIPT:

facts
style
duration
prompt version
LLM config

STORYBOARD:

script
style
prompt version

TTS:

narration
voice
provider
config

ALIGNMENT:

audio
alignment config

VISUAL:

type
prompt
source
workflow
config

SCENE:

visual
audio
captions
template

FINAL:

scene outputs
transitions
video settings

---

# 50. GPU STRATEGY

Avoid keeping all large models active simultaneously.

Preferred processing:

LLM
↓
TTS
↓
Alignment
↓
ComfyUI
↓
Rendering

Profiles:

LOW
~6GB VRAM

MEDIUM
8–12GB

HIGH
16–24GB

Profiles belong in configuration.

---

# 51. SECURITY

Article HTML is untrusted.

Sanitize HTML/text.

Never execute scraped scripts.

Validate project IDs.

Prevent path traversal.

Use subprocess safely.

Avoid shell=True.

Set service timeouts.

Bound retries.

Never retry expensive generation indefinitely.

---

# 52. PHASE 0

## UPSTREAM AUDIT + FOUNDATION

Before implementation:

clone upstream repositories.

Inspect actual source.

Create:

UPSTREAM_REUSE_AUDIT.md
UPSTREAM_SOURCE_MAP.md
THIRD_PARTY_NOTICES.md

Then implement:

repository foundation
Python package
CLI skeleton
configuration
logging
Pydantic core schemas
project manager
checkpoint model
doctor
pytest
AGENTS.md
ARCHITECTURE.md
README.md

Acceptance:

CLI runs.
Tests run.
Project creation works.
Checkpoint persists.
Doctor reports dependencies.
Reuse audit exists.
Source map exists.
Licensing documented.

STOP.

---

# 53. PHASE 1

## URL → ARTICLE

Inspect upstream first.

Especially:

html-video source URL handling
Videogen article handling
newsvid URL workflow

Reuse/adapt before new implementation.

Implement:

static extraction
Trafilatura where useful
Playwright fallback
metadata
images
local HTML fixture

Outputs:

source.json
article.md
images.json

Acceptance:

real URL supported
local fixture supported
fallback supported
schemas valid

STOP.

---

# 54. PHASE 2

## ARTICLE → FACTS

Inspect:

Videogen LLM
newsvid Ollama

Reuse provider/config/retry infrastructure.

Implement:

LLMProvider
OllamaProvider
fact extraction
structured parsing
schema validation
fact IDs
evidence
confidence
importance

Output:

facts.json

Acceptance:

valid facts
unique IDs
evidence present
invalid model output handled
tests pass

STOP.

---

# 55. PHASE 3

## FACTS → VIETNAMESE SCRIPT

Inspect:

Videogen generation
Auto-Create-Video Vietnamese workflow
newsvid news prompts

Reuse/adapt.

Implement:

Vietnamese script
duration targeting
styles
fact references

Output:

script.json

Acceptance:

all factual segments have valid fact_refs
Vietnamese output
duration approximately respected

STOP.

---

# 56. PHASE 4

## SCRIPT → STORYBOARD

Inspect deeply:

html-video content graph
Auto-Create-Video scene system
Videogen scene/media planning

Reuse/adapt representation where beneficial.

Implement:

storyboard schema
scene types
VisualRouter
template selection
fact propagation

Output:

storyboard.json

Acceptance:

schema valid
human editable
visual decisions valid
fact refs preserved

STOP.

---

# 57. PHASE 5

## VIETNAMESE TTS

Inspect Videogen TTS/cache.

Inspect Auto-Create-Video Vietnamese narration.

Reuse/adapt.

Implement:

TTSProvider
PiperProvider
F5TTSProvider
normalize_vi
pronunciation dictionary
audio cache

Acceptance:

Vietnamese WAV
cache works
numbers/dates/percentages normalized
F5 optional

STOP.

---

# 58. PHASE 6

## ALIGNMENT + SUBTITLES

Reuse Videogen aggressively.

Inspect:

word timestamps
STT
ASS
karaoke
subtitle layout

Implement/adapt:

WhisperX provider
words.json
ASS
karaoke
safe area
overflow validation

Acceptance:

subtitle timing follows audio
ASS renders
Vietnamese works
overflow validation works

STOP.

---

# 59. PHASE 7

## ARTICLE-ASSET VIDEO

Reuse Videogen heavily.

Implement/adapt:

image caching
crop
resize
Ken Burns
pan/zoom
FFmpeg scene generation
caption composition
audio composition

Must work WITHOUT ComfyUI.

Acceptance:

article
→ voice
→ captions
→ article imagery
→ vertical MP4

STOP.

---

# 60. PHASE 8

## MOTION GRAPHICS

Primary:

Auto-Create-Video
html-video

Reuse:

HyperFrames
GSAP
Chromium
template runtime
animation
rendering

Templates:

hook
headline
stat-hero
chart
comparison
timeline
quote
outro

Acceptance:

templates render independently
structured input
FFmpeg integration
1080×1920 compatible

STOP.

---

# 61. PHASE 9

## COMFYUI

Reuse Videogen ComfyUI implementation.

Implement adapter:

ComfyUIProvider

Workflows:

news-image
background
infographic

Implement:

queue
poll
collect
cache
error handling

Acceptance:

AI image generated
cached
pipeline survives service failure
resume works

STOP.

---

# 62. PHASE 10

## FULL VIDEO ASSEMBLY

Reuse:

Videogen FFmpeg
html-video rendering/export
Auto-Create-Video composition ideas

Normalize to:

SceneRenderer
↓
RenderedScene
↓
FinalAssembler

Implement:

transitions
audio
captions
motion scenes
image scenes
final concat
preview

Acceptance:

1080×1920
30fps
H.264
AAC
preview works

STOP.

---

# 63. PHASE 11

## SELECTIVE REGENERATION

Reuse Videogen checkpoint/cache.

Implement dependency-aware invalidation.

Narration change:

TTS
alignment
caption
scene

Visual change:

visual
scene

Unrelated scenes:

CACHE HIT

Acceptance:

tests prove unrelated assets remain unchanged.

STOP.

---

# 64. PHASE 12

## AUTOMATED QA

Reuse upstream validation where appropriate.

Implement:

fact refs
missing media
audio
captions
safe areas
duration
resolution
blank scenes
duplicate visuals
render errors

Output:

qa.json

Acceptance:

critical QA failure produces non-zero status.

STOP.

---

# 65. PHASE 13

## CODEX + CURSOR TOOLS

Reuse html-video heavily.

Inspect:

agent detection
Codex adapter
Cursor adapter
agent execution
content graph editing
per-frame rerender

Adapt to our project.

Tools:

fetch_article
generate_script
generate_tts
generate_visual
render_scene
render_video
inspect_video
validate_project

Acceptance:

Codex edits storyboard
→ validate
→ rerender one scene

STOP.

---

# 66. PHASE 14

## AUTONOMOUS EDITOR

Reuse/adapt html-video agent iteration.

Workflow:

inspect
↓
edit storyboard
↓
validate
↓
rerender changed scenes
↓
preview
↓
QA

Maximum:

3 revisions

Acceptance:

agent improves preview without regenerating unrelated assets.

STOP.

---

# 67. PHASE 15

## FASTAPI

Implement thin API adapter.

Do not duplicate pipeline logic.

Expose:

projects
generation
scenes
preview
render
QA
services

Acceptance:

all core workflows accessible through API.

STOP.

---

# 68. PHASE 16

## WEB STUDIO

Inspect/reuse html-video Studio architecture where useful.

Implement:

Projects
Create
Article
Facts
Script
Storyboard
Scene Editor
Preview
QA
Settings
Services

Acceptance:

URL → MP4 possible without terminal.

STOP.

---

# 69. PHASE 17

## ADVANCED VISUALS

Optional.

Integrate through ComfyUI/provider interfaces.

Potential:

Wan
LTX
AnimateDiff
other image-to-video

Must remain optional.

Acceptance:

existing pipeline still works with advanced services disabled.

STOP.

---

# 70. PHASE 18

## DESKTOP

Optional.

Tauri wrapper.

Connect to existing backend/services.

Do not duplicate pipeline.

Do not bundle large models.

Acceptance:

local Studio launches through desktop application.

STOP.

---

# 71. DEFINITION OF DONE — EVERY PHASE

Before declaring phase complete:

1. inspect relevant upstream source;
2. update reuse audit;
3. update source map;
4. verify licenses;
5. implement;
6. port upstream tests where useful;
7. run unit tests;
8. run integration tests;
9. run acceptance criteria;
10. update documentation;
11. verify no premature next-phase implementation;
12. produce phase report.

---

# 72. MANDATORY PHASE REPORT

Use exactly:

==================================================
PHASE X COMPLETE
================

STATUS:
PASS / FAIL / BLOCKED

## IMPLEMENTED:

## UPSTREAM CODE REVIEWED:

## DIRECTLY REUSED:

## ADAPTED:

## EXTENDED:

## WRITTEN NEW:

## WHY NEW CODE WAS NECESSARY:

## UPSTREAM TESTS PORTED:

## FILES ADDED:

## FILES MODIFIED:

## LICENSE / ATTRIBUTION CHANGES:

## TESTS RUN:

## TEST RESULTS:

ACCEPTANCE CRITERIA:
[ ] ...
[ ] ...

## KNOWN LIMITATIONS:

ARCHITECTURAL DEVIATIONS:
NONE
or
--

NEXT PHASE READY:
YES / NO

==================================================
STOP POINT
==========

Phase X is complete.

DO NOT START PHASE X+1.

Wait for the next explicit user prompt.

==================================================

If STATUS != PASS:

NEXT PHASE READY must be NO.

Do not continue.

---

# 73. STRICT STOP RULE

THIS RULE OVERRIDES AUTONOMOUS CONTINUATION.

When a phase is complete:

STOP EXECUTION.

Do not:

start next phase
prepare next phase implementation
create next-phase modules
implement convenient future features
continue because context is available

Only output the Phase Completion Report.

Wait for user.

---

# 74. NO PLACEHOLDER RULE

Do not create fake future implementations.

Forbidden:

pass-only service classes
fake adapters
dummy renderers
TODO implementations pretending to work

Future functionality remains documented until its phase.

---

# 75. NO DUPLICATE IMPLEMENTATION RULE

Before creating a significant implementation:

search:

our codebase
Videogen
Auto-Create-Video
html-video
newsvid

If suitable implementation exists:

reuse/adapt/extend.

Do not create competing implementations.

---

# 76. MVP

MVP command:

newsvid create "<ARTICLE_URL>" 
--duration 60 
--lang vi 
--style tech-news 
--visual hybrid

Output:

projects/<id>/output/final.mp4

Must contain:

grounded facts
Vietnamese script
Vietnamese narration
word-aligned subtitles
article visuals
motion graphics
optional AI imagery
1080×1920
checkpoint/resume
cache
selective rerender

---

# 77. V1

V1:

MVP
+
ComfyUI
+
Piper
+
F5-TTS
+
WhisperX
+
motion templates
+
QA
+
Codex/Cursor tools
+
autonomous editor
+
FastAPI
+
Web Studio

---

# 78. ENGINEERING PRIORITIES

Priority order:

1. factual correctness
2. upstream reuse
3. reliability
4. resumability
5. deterministic caching
6. editability
7. selective regeneration
8. output quality
9. performance
10. UI polish

---

# 79. FINAL PRODUCT

The final system must behave as:

ARTICLE URL
↓
AI NEWS PRODUCTION PIPELINE
↓
FACT-GROUNDED SCRIPT
↓
STORYBOARD
↓
HYBRID VISUAL DIRECTOR
↓
VIETNAMESE VOICE
↓
WORD-LEVEL CAPTIONS
↓
MOTION GRAPHICS
↓
PREVIEW
↓
AUTOMATED QA
↓
AGENT EDITING
↓
FINAL MP4

The goal is NOT an AI slideshow generator.

The goal is a:

LOCAL AUTONOMOUS AI NEWS VIDEO STUDIO.

Reuse proven upstream engineering wherever possible.

Adapt it into a coherent architecture.

Extend it where product requirements differ.

Write new code only where upstream solutions are insufficient.
