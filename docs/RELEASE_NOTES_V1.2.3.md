# Super Video Pro 1.2.3

V1.2.3 adds an FxTwitter fallback for X posts that the guest yt-dlp extractor cannot see.

## Added and fixed

- Retains yt-dlp as the preferred local-first X extractor.
- Falls back to the MIT-licensed FxEmbed/FxTwitter API when yt-dlp finds no media.
- Parses and ranks direct MP4 variants from Twitter's media CDN.
- Accepts fallback downloads only from HTTPS `video.twimg.com` URLs.
- Applies a 15-second timeout and a 1 MB metadata-response limit.
- Does not transmit browser cookies to FxTwitter.

## Reported URL

The supplied sensitive X post now resolves to three MP4 variants, including 1280×720. The 480×270 variant was downloaded and validated locally as a 417.146-second MP4 with H.264 video and AAC audio.
