# Super Video Pro 1.13.0

## Summary

This release completes the media-oriented presentation migration while preserving the existing Electron, IPC, SQLite, FastAPI, Python coordinator and FFmpeg boundaries. It also hardens the AI News workflow so users can create or preview a video without manually walking through every internal stage.

## Highlights

- Professional Compose layout: media bin, live preview, properties inspector and multi-track timeline.
- One-click AI News complete render, captioned preview and quick preview.
- Automatic setup/recovery for Ollama, Piper Vietnamese voice and WhisperX.
- Service-discovered model selectors instead of free-text configuration.
- Preview-aware QA with readable checks and a direct final-render action.
- Grounding, script reference, TTS manifest, Chromium and conditional ComfyUI fixes.
- Automatic tag-based GitHub Release workflow for the Windows installer and SHA-256 checksum.

## Architecture preservation

Clypra was used only as a presentation and interaction reference. No Tauri or Rust runtime was imported. Electron remains the desktop shell; the renderer continues to call allowlisted IPC and loopback FastAPI interfaces, and server-owned jobs remain authoritative.

## Installation

Download `Super Video Pro Setup 1.13.0.exe`, verify it against `SHA256SUMS.txt`, run the installer and choose an installation directory. Windows may warn because the installer is not Authenticode-signed.

## Known limitations

- ComfyUI is optional and must be installed/run separately for scenes explicitly routed to generated imagery.
- The installer does not bundle large AI model weights; trusted local setup downloads them on demand.
- Windows code signing is not configured.
- Real-site extraction can change when external sites change and is tested separately from deterministic CI.

## Rollback

Uninstall 1.13.0 and reinstall the previous published installer. User data under the Electron user-data directory is not removed by application uninstall; back it up before any manual deletion.
