# Supported media matrix

| Input | V1 behavior | Runtime | Notes |
|---|---|---|---|
| Direct HTTP(S) MP4/WebM/audio | Native ranged download with `.part` resume | Built in | Final FFprobe validation when available |
| HLS `.m3u8` | Manifest discovery and FFmpeg remux | Bundled FFmpeg | Encrypted/DRM playlists are unsupported |
| DASH `.mpd` | Manifest discovery and FFmpeg remux | Bundled FFmpeg | DRM representations are unsupported |
| Supported web page | yt-dlp inspection/download | Bundled pinned yt-dlp | Optional Edge/Chrome/Firefox cookie source |
| X/Twitter post video | yt-dlp, then FxTwitter fallback | Bundled yt-dlp / FxEmbed API | FxTwitter fallback accepts only HTTPS media from `video.twimg.com`; no browser login is required for posts exposed by FxEmbed |
| Generic HTML media tags/URLs | HTML discovery, then native/FFmpeg engine | Built in | Relative and escaped URLs supported |
| Dynamic browser-loaded media | Ephemeral sandboxed browser sniffer | Electron Chromium | Storage is cleared after inspection |
| Subtitles exposed by source | Preserved in normalized contract | Extractor-dependent | Muxing policy is source/format dependent |
| DRM/protected media | Clear unsupported/protected outcome | None | No DRM bypass |

Unknown extractor, protection and error values degrade safely. A failed source or job cannot stop unrelated queue work.
