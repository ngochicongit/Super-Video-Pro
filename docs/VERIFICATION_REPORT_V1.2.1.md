# Super Video Pro 1.2.1 — Verification Report

Verification date: 2026-08-24 (Asia/Saigon)

## Automated verification

- `pnpm verify`: PASS.
- TypeScript: PASS.
- Vitest: 13 files, 34 tests passed.
- Renderer/Electron production build: PASS.
- Bundled Deno 2.9.5 resolution and execution: PASS.

## Reported YouTube URL proof

- URL: `https://www.youtube.com/watch?v=NY8DFKi2DNY&list=RDMMNY8DFKi2DNY&start_radio=1`.
- The real Electron renderer inspected the URL, selected a variant, downloaded video and audio through yt-dlp, merged the streams, validated the output and reached `completed`.
- Output: `outputs/runtime/youtube-fix-download-v3/Jiang Xue Er (蒋雪儿) - Mo Wen Gui Qi (莫问归期) Lyrics 歌词 Pinyin⧸English Translation (動態歌詞) [NY8DFKi2DNY].mkv`.
- Output size: 4,014,803 bytes.
- Evidence: `outputs/runtime/youtube-fix-ui-v3.png` and its JSON smoke result.

## Packaged application proof

- Final NSIS installer clean-installed with exit code 0 into an isolated directory.
- Packaged application loaded from `app.asar`; bundled yt-dlp, Deno, FFmpeg and FFprobe were present.
- The packaged UI repeated the exact reported URL test and reached `completed` for the target job.
- Final evidence: `outputs/runtime/youtube-fix-final-ui.png`, its JSON result and `outputs/runtime/youtube-fix-final-download/`.
- Output size: 4,014,803 bytes; SHA-256: `C6CC6387A2A2E8298BAB18282EBAB8E88E122EC5035E3228C735DB67886F223C`.
- Silent uninstall returned exit code 0 and removed the isolated final installation directory.

## Release artifact

- File: `release/Super Video Pro Setup 1.2.1.exe`.
- Size: 271,763,245 bytes.
- SHA-256: `817E53398774348112FB6007FE666E62D87F056D5311A6FF08BFD78E15D12B89`.

## Result

The reported YouTube failure is fixed and V1.2.1 is approved for handoff.
