# Super Video Pro 1.7.0

## Editing workflow

- Split the selected video clip at the current playhead position.
- Split calculations account for source trim and clip playback speed.
- Multiple segments may safely reference the same source file and render as independent FFmpeg inputs.
- Undo and redo up to 40 timeline states with toolbar actions or Ctrl+Z and Ctrl+Y.
- Save and restore the current project locally on the device.

## Validation

- Timeline contracts distinguish accidental duplicate inputs from intentional split segments.
- UI coverage verifies split, history and local project persistence controls.
- Production visual smoke verifies the expanded project toolbar and timeline layout.

## Release evidence

- Installer: `Super Video Pro Setup 1.7.0.exe`
- Size: `271413283` bytes
- SHA-256: `1089076DDDCD5508B2CEB9FDDD35DF6835191B39AE39E9FF272E8D645F99C276`
- Typecheck, 118 tests, production build, visual smoke and packaged-app smoke passed.
- Authenticode: not signed.
