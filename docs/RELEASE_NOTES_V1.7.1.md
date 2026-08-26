# Super Video Pro 1.7.1

## Editor fixes

- Timeline seeking now applies the resolved edited clip time after the playhead changes instead of using stale React state.
- Video playback updates the global timeline playhead using trim and speed-aware source-time mapping.
- Logo overlays can be selected and dragged freely on the preview canvas.
- Custom percentage coordinates are validated and exported through FFmpeg.
- Bounce, horizontal and vertical logo movement now animate in the preview; FFmpeg remains authoritative for final motion rendering.
- Preview only shows overlays inside their configured timeline range.

## Research

- Added a license-aware comparison of OpenScene, Elah, OpenVideo Editor, Twick, OpenShot and Olive.
- No external repository code was copied in this release.

## Release evidence

- Installer: `Super Video Pro Setup 1.7.1.exe`
- Size: `271413839` bytes
- SHA-256: `874531D80776862AB71BA905A64E01E3D2F1587D7A3F7F51F41E922AA50A4260`
- Typecheck, 119 tests, production build and packaged-app smoke passed.
- Authenticode: not signed.
