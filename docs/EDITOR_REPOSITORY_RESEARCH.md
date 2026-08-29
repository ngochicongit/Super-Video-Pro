# Editor repository research

Reviewed on 2026-08-27. Star counts are snapshots and may change.

## Recommended references

### OpenScene

- Repository: https://github.com/Theorvane/openscene
- Stack: Electron, React, TypeScript, local FFmpeg.
- License: MIT.
- Best architectural match for this project: typed preload bridge, local projects, shared timeline rules, program monitor, FFmpeg-authoritative export, trim/split/move/undo and keyframes.
- Community is currently small, so reuse should be selective and backed by our own tests.

### Elah

- Repository: https://github.com/elahlabs/elah
- Stack: framework-independent timeline core, React bindings, WebGL preview and MP4 export.
- License: Apache-2.0.
- Strong reference for deterministic playback, a renderer-independent project model and frame-accurate timeline resolution.
- Young project; evaluate package stability before adding it as a dependency.

### OpenVideo Editor

- Repository: https://github.com/openvideodev/react-video-editor
- Around 1.8k stars at review time.
- Strong CapCut/Canva-style UI and React timeline reference.
- License is not generally permissive: free use is limited to individuals, non-profits and organizations with up to three employees; larger organizations require a company license. Study patterns, but do not copy or vendor code without confirming eligibility.

### Twick

- Repository: https://github.com/ncounterspecialist/twick
- Around 531 stars at review time.
- React canvas, multi-track timeline, captions, WebGL effects and MP4 export.
- Sustainable Use License permits use inside an end-user product but restricts standalone SDK resale/rebranding. Confirm distribution fit before code reuse.

## Mature desktop UX references

### OpenShot

- Repository: https://github.com/OpenShot/openshot-qt
- Around 6.2k stars at review time; GPL desktop application.
- Useful UX reference for advanced timeline, snapping, waveform, transform handles, keyframes, transitions, proxy editing and export options.
- Python/Qt/libopenshot architecture is not directly compatible with this Electron/React codebase. GPL code should not be copied into this differently licensed product without accepting GPL obligations.

### Olive

- Repository: https://github.com/olive-editor/olive
- Around 9.1k stars at review time; GPL-3.0 C++/Qt editor.
- Useful for node-based compositing and professional NLE interaction research, but the project describes its current build as alpha/unstable and its code is not a direct fit.

## Decision

Use OpenScene as the closest architectural reference and Elah for deterministic timeline ideas. Use OpenVideo Editor, Twick, OpenShot and Olive as interaction/feature references subject to their licenses. No external repository code was copied into Super Video Pro during this bug-fix pass.

## Adopted OpenShot UX principles

- One authoritative timeline coordinate system must drive playhead, trim, preview and export.
- Snapping applies to frame boundaries, the playhead and clip edges; it remains an explicit toggle.
- Frame-step controls sit beside the main editing actions for precise slicing.
- Zoom should preserve the playhead context instead of changing the perceived edit position.
- Future direct trim handles must show live feedback, ignore self-snapping and commit one undo transaction per drag.
- Waveforms and thumbnails are cached presentation data, never the source of timeline truth.

## Technology boundary

- Renderer/frontend remains Electron, React and TypeScript.
- Shared timeline contracts remain serializable and language-neutral.
- Backend workers may use Node.js, Rust, Python or C++ when profiling shows a concrete benefit.
- Every non-Node worker must be an isolated process behind validated IPC, bounded input/output, cancellation, timeouts and deterministic tests.
- External repositories are reviewed statically. They are not cloned wholesale, executed, or imported without a separate license and dependency review.

## Timeline component decision (2026-08-27)

- [`@xzdarcy/react-timeline-editor`](https://github.com/xzdarcy/react-timeline-editor) is the preferred incremental replacement for the hand-built interaction layer. It is MIT licensed, React-native, and already supplies action drag/resize, timeline scale and controlled data. Our FFmpeg/project model can remain unchanged behind an adapter.
- [`AiCut`](https://github.com/ipmotionmc/AiCut) has an attractive MIT React editor and canvas timeline, but its published roadmap still lists speed adjustment and waveform thumbnails as incomplete. It is useful for UX study, not a safe drop-in dependency for the current release.
- [`Frontstage`](https://github.com/x777/frontstage) demonstrates a strong Electron/React professional timeline, but it is GPL-3.0 and cannot be copied into this project without accepting GPL obligations.
- OpenShot remains a UX reference for dedicated zoom/pan controls, snapping and distinct drag handles. Its Qt timeline cannot be embedded directly into the Electron/React renderer.

The current patch fixes the release-blocking interactions without adding a dependency. A later migration can replace only the timeline view with `@xzdarcy/react-timeline-editor`, using a two-way adapter to the existing clip, logo, lock/mute, undo and FFmpeg contracts; this avoids rewriting the rest of the editor.
