# Super Video Pro 1.2.2 — Verification Report

Verification date: 2026-08-24 (Asia/Saigon)

## Automated verification

- `pnpm verify`: PASS.
- TypeScript: PASS.
- Vitest: 13 files, 35 tests passed.
- Browser-cookie propagation into inspection: covered by automated test.

## X/Twitter proof

- Public X/Twitter reference URL from the official yt-dlp extractor test set was inspected by `yt-dlp`.
- Six video variants were normalized into the application media contract.
- The selected variant downloaded successfully as MP4.
- Output size: 16,402,413 bytes.
- Evidence: `outputs/runtime/x-public-download/`.

## Reported URL boundary

- URL: `https://x.com/truckaml/status/2089323308768797051?s=20`.
- X labels the post as sensitive and only exposes it to an authenticated app/session.
- Guest extraction correctly reports that no video is visible.
- V1.2.2 now uses the selected signed-in browser during inspection and download; exact retrieval therefore requires an available authenticated X cookie database.

## Packaged application proof

- Final NSIS installer clean-installed with exit code 0 into an isolated directory.
- Packaged application loaded from `app.asar`, inspected a public X post, downloaded its selected variant and reached `completed` for the target job.
- Packaged output size: 4,129,287 bytes; SHA-256: `9A3798A449BC850BB7D52C6C727AB565927EAB42ACCA5524ACC52C88E4937C11`.
- Evidence: `outputs/runtime/x-final-ui.png`, its JSON result and `outputs/runtime/x-final-download/`.
- Silent uninstall returned exit code 0 and removed the isolated installation directory.

## Release artifact

- File: `release/Super Video Pro Setup 1.2.2.exe`.
- Size: 271,763,312 bytes.
- SHA-256: `4584E54B0D086DD70F1FF1FD0D52EE342790380B4F7FB878DB52AEF6442F3987`.

## Result

X/Twitter video support is implemented, packaged and approved for handoff. The supplied sensitive post requires an authenticated X browser session as enforced by X.
