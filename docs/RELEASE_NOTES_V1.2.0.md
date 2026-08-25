# Super Video Pro 1.2.0

V1.2 completes the desktop download experience and replaces the native Windows chrome with a branded interface.

## Added

- Explicit two-step download flow: inspect a URL, select quality, then choose **Tải xuống**.
- Structured local debug events for renderer readiness, inspect success/failure, downloads, queue commands, settings, filters, file reveal, diagnostics export, update checks and window controls.
- Vietnamese UI catalog in `src/locales/vi.json`; application source references translation keys and contains no embedded non-ASCII UI text.
- Frameless window with draggable custom title bar and compact close/minimize/maximize controls.
- New Super Video Pro play/download icon for the title bar, executable and NSIS installer.
- Smooth hover, focus, press and progress transitions with `prefers-reduced-motion` accessibility support.

## Verification

The packaged UI completed a real MP4 download through the visible inspect/download flow. See `docs/VERIFICATION_REPORT_V1.2.0.md`.
