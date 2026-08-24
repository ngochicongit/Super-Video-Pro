# Super Video Pro 1.2.3 — Verification Report

Verification date: 2026-08-24 (Asia/Saigon)

## Automated verification

- `pnpm verify`: PASS.
- TypeScript: PASS.
- Vitest: 13 files, 37 tests passed.
- FxTwitter response parsing, quality ordering and untrusted-domain rejection: PASS.

## Exact reported URL proof

- URL: `https://x.com/truckaml/status/2089323308768797051?s=20`.
- Extractor: `fxtwitter` fallback after yt-dlp guest extraction returned no media.
- Variants: 480×270, 640×360 and 1280×720 MP4.
- Downloaded test variant: 480×270 MP4, 7,161,899 bytes.
- FFprobe: H.264 video, AAC audio, duration 417.146 seconds.
- Evidence: `outputs/runtime/x-exact-fxtwitter-download/Truck Senpai - X 2089323308768797051.mp4`.

## Packaged application proof

- Final NSIS installer clean-installed with exit code 0 into an isolated directory.
- Packaged application loaded from `app.asar`, inspected the exact reported URL, selected 1280×720, downloaded, validated and rendered `completed` for the target job.
- Packaged output: 51,008,280 bytes; SHA-256: `EE0E17C71A2F3F2340FEE4B503026A3ADFC30C9C4839923894D7C5ACDB3FA857`.
- FFprobe: 1280×720 H.264 video, AAC audio, duration 417.146 seconds.
- Evidence: `outputs/runtime/x-exact-final-v2-ui.png`, its JSON result and `outputs/runtime/x-exact-final-v2-download/`.
- Silent uninstall returned exit code 0 and removed the isolated installation directory.

## Release artifact

- File: `release/Super Video Pro Setup 1.2.3.exe`.
- Size: 271,764,997 bytes.
- SHA-256: `C3FFD00B9A636516B5DC3E5F8191B874DEA010BD1E33B4E56C22E23D7FE6F0B1`.

## Result

The exact X video reported by the user downloads successfully through the packaged UI. V1.2.3 is approved for handoff.
