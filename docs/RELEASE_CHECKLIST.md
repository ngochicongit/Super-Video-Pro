# V1 release gate

- [x] `pnpm verify` passes.
- [x] `pnpm package` produces the NSIS installer.
- [x] `win-unpacked/Super Video Pro.exe` remains running during the production smoke window.
- [x] Direct fixture download matches the expected bytes and leaves no `.part` file.
- [x] Pause/resume/cancel/retry and restart recovery are exercised.
- [x] HLS/DASH/yt-dlp checks run when their tools are available; missing tools produce an actionable error.
- [x] Malformed IPC payloads are rejected.
- [x] Final invalid/empty files never become `completed`.
- [x] Diagnostic secret corpus is fully redacted.
- [x] No unresolved Critical/P0 blocker remains.
- [x] Release notes, known issues and rollback owner are recorded.

Latest gate closure: V1.10.0 local release candidate on 2026-08-28. Verification and installer evidence are recorded in `docs/RELEASE_NOTES_V1.10.0.md`; no external publication is claimed.
