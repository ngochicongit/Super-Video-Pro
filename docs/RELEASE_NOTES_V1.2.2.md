# Super Video Pro 1.2.2

V1.2.2 adds X/Twitter video support to both URL inspection and download execution.

## Added and fixed

- Passes the selected Edge, Chrome or Firefox cookie source into yt-dlp during inspection, not only during the later download step.
- Supports public X/Twitter post videos through the existing quality selection and validated download flow.
- Supports sensitive or account-only X posts when the selected browser has a signed-in X session and its cookie database is available.
- Retains the public retry path when Chromium's cookie database is locked.
- Recognizes X/Twitter status IDs when resolving Unicode output paths on Windows.

## Reported URL

The supplied post is marked sensitive by X and is exposed only to an authenticated session. Select a browser signed in to X and close that browser before inspection if Chromium reports that its cookie database is locked.
