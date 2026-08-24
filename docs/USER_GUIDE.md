# User guide

1. Paste a lawful media URL and choose **Inspect URL**.
2. Review the discovered title and select a quality/format variant.
3. Choose a download directory and concurrency, then add the job.
4. For multiple URLs, switch to **Batch** and enter one URL per line. Batch items use the first recommended variant and remain isolated from one another.
5. Use pause, resume, cancel or retry on queue items. Partial direct downloads are retained for resume. A processing/validation retry reuses the downloaded artifact.
6. Use queue search and the status filter to narrow long histories. **Show file** reveals a finished output in Explorer. **Remove** deletes only the history record, not the downloaded file; **Clear finished** removes completed/cancelled history while leaving active and failed work untouched.

When an output name already exists, the existing file is preserved and the new download receives a numbered name such as `video (2).mp4`.

For authenticated sources, select a browser under **Cookies**. The app asks bundled yt-dlp to read that browser's existing cookie store; it does not persist plaintext cookies in its database.

On public YouTube videos, if Chromium has locked its cookie database, the app automatically retries without browser cookies. For age-restricted, private or account-only media, close the selected browser before retrying or select a browser whose cookie store is available.

The runtime badges report bundled yt-dlp, Deno, FFmpeg and FFprobe versions. Deno is used by yt-dlp for current YouTube player extraction. If a job fails, the message stays attached to the job. **Export diagnostics** writes a redacted JSONL report chosen by the user. No telemetry is sent.

Completed status is gated by final file existence, non-zero size, container parsing and audio/video stream validation. Invalid output remains failed and is never presented as a successful final file.
