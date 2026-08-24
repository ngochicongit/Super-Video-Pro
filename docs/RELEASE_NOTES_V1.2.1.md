# Super Video Pro 1.2.1

V1.2.1 repairs YouTube downloads affected by current player extraction and locked Chromium cookie databases.

## Fixed

- Bundled Deno 2.9.5 and passed it explicitly to yt-dlp as the JavaScript runtime.
- Selected yt-dlp's embedded web YouTube client to avoid the HTTP 403 response seen with the previous default client.
- Retried public media without browser cookies when Chromium prevents yt-dlp from copying its locked cookie database.
- Resolved the final yt-dlp output by video ID and filesystem metadata when Windows stdout cannot faithfully represent a Unicode filename.
- Included Deno in tool status reporting, reproducible tool preparation and installer resources.

## Verification

The exact reported YouTube URL completed through the real Electron interface and produced a validated 4,014,803-byte media file. See `docs/VERIFICATION_REPORT_V1.2.1.md`.
