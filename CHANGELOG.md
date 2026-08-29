# Changelog

All notable user-facing changes are recorded here.

## [1.13.0] - 2026-08-30

### Added

- Media-oriented Compose workspace with media bin, preview canvas, multi-track timeline and contextual properties.
- AI News one-click complete-video, quick-preview and captioned-preview workflows.
- Typed dependency preflight with safe automatic repair and actionable service status.
- Automatic local Ollama, Piper voice and isolated WhisperX setup.
- Discovered model, provider, voice and checkpoint selectors.
- Readable QA checklist with preview-aware validation and direct final-render recovery.
- Tag-triggered Windows GitHub Release workflow with installer and SHA-256 artifact.

### Changed

- Expanded the desktop product from a downloader into a unified download, composition and AI news production workspace.
- Improved News Studio progress, checkpoint reconciliation and selective regeneration.
- Selected WhisperX `small` CPU `int8` as the reliable default for constrained Windows GPUs.

### Fixed

- Grounded fact evidence validation and factual script `fact_refs` recovery.
- Missing TTS manifest dependency ordering during scene rendering.
- Electron embedded Node invocation for Playwright rendering.
- Conditional ComfyUI preflight so graphic/article scenes do not require an offline image service.
- QA no longer reports a missing final render manifest as a file exception when a valid preview exists.

### Preserved

- Electron shell and allowlisted IPC.
- Existing SQLite storage, queue and job lifecycle.
- Python/FastAPI coordinators, project schemas and checkpoint boundaries.
- FFmpeg/FFprobe rendering and validation chain.
- Existing local-first privacy and diagnostic redaction policy.

### Packaging

- NSIS remains the Windows installer target.
- Python/FastAPI and portable runtime tools remain packaged as Electron resources.
- AI model weights remain outside the installer and are set up locally on demand.

### Documentation

- Added dependency preflight, UI repository analysis, release notes and updated architecture/setup guidance.
