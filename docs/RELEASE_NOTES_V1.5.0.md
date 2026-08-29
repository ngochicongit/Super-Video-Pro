# Super Video Pro 1.5.0

## Timeline editor MVP

- Replaces the composition form with a three-pane non-linear editing workspace.
- Adds a media library, video preview, transport controls, playhead and timeline zoom.
- Adds VIDEO, AUDIO and OVERLAY tracks scaled from FFprobe media durations.
- Supports drag-and-drop video ordering, clip selection and timeline deletion.
- Adds a contextual inspector for media metadata and logo appearance/movement controls.
- Keeps export connected to the validated multi-video, audio and multi-logo FFmpeg pipeline.

## Scope

- This release establishes the editor foundation. Free-form trimming, splitting, transitions, keyframes, text tracks, undo history and project persistence require a versioned timeline render model and are not represented by inactive controls in this MVP.

## Release evidence

- Installer: `Super Video Pro Setup 1.5.0.exe`
- Size: `271411512` bytes
- SHA-256: `C7EDC576D95F2BA62225B9557245D6D86BF827E9F92C19F0218C17B258B57C4D`
- Typecheck, 114 tests, production build and packaged-app smoke passed.
- Authenticode: not signed.
