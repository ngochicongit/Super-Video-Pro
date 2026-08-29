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

## V1.13.0 local release evidence — 2026-08-30

- [x] `pnpm ui:verify`: 100/100 across Download, Compose, AI News Studio, History, Tasks and Settings at 1280x720, 1366x768 and 1920x1080.
- [x] `pnpm verify`: TypeScript, 38 Vitest files/150 tests and production renderer build pass.
- [x] Python suite: all configured tests pass; one optional runtime acceptance test is skipped.
- [x] `pnpm audit --prod`: no known vulnerabilities.
- [x] `pnpm smoke:real`: public direct MP4 and HLS inspection pass.
- [x] `new-87ff67` QA: grounded references, durations, duplicate checks, 1080x1920/30 fps preview and AAC audio pass.
- [x] `pnpm package`: `Super Video Pro Setup 1.13.0.exe` created (321,601,623 bytes).
- [x] Installer SHA-256: `BD5197E005777273EA0DD687B731F4DFBB6EC98B089C9B47CB3ADC7503314D15`.
- [x] Clean isolated install, packaged application launch, backend `/health` response and silent uninstall pass.
- [x] Authenticode checked explicitly: installer is unsigned and the limitation is disclosed in the release notes.
- [ ] GitHub Actions and published release evidence are recorded after the tag workflow completes.

The local V1.13.0 candidate passes every locally executable release gate. External publication is intentionally not claimed until GitHub authentication, protected-branch checks and the tag release workflow complete.
