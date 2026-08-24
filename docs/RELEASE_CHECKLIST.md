# V1 release gate

- [ ] `pnpm verify` passes.
- [ ] `pnpm package` produces the NSIS installer.
- [ ] `win-unpacked/Super Video Pro.exe` remains running during the production smoke window.
- [ ] Direct fixture download matches the expected bytes and leaves no `.part` file.
- [ ] Pause/resume/cancel/retry and restart recovery are exercised.
- [ ] HLS/DASH/yt-dlp checks run when their tools are available; missing tools produce an actionable error.
- [ ] Malformed IPC payloads are rejected.
- [ ] Final invalid/empty files never become `completed`.
- [ ] Diagnostic secret corpus is fully redacted.
- [ ] No unresolved Critical/P0 blocker remains.
- [ ] Release notes, known issues and rollback owner are recorded.
