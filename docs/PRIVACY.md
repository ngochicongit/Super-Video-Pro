# Privacy and lawful-use policy

Super Video Pro is local-first. Queue state, settings, artifacts and diagnostics remain on the user's device. The application contains no telemetry endpoint and does not silently upload diagnostics.

For an X/Twitter URL that yt-dlp cannot inspect, the application sends the public post handle and status ID to `api.fxtwitter.com` to discover media variants. The returned media URL is accepted only when it uses HTTPS on Twitter's `video.twimg.com` CDN. Browser cookies are not sent to FxTwitter.

Diagnostic export is an explicit user action. Cookie, authorization, token, password and secret-like values are redacted. Credential material that the application must retain uses the operating system encryption facility; plaintext cookie persistence is prohibited.

The application is for media the user is authorized to download. It does not bypass DRM, defeat access controls or promise compatibility with protected/unsupported services. Site terms and applicable law remain the user's responsibility.
