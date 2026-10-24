---
name: YouTube audio download validation
description: Third-party downloader APIs can return non-audio bytes despite a successful HTTP response.
---

Treat provider audio downloads as untrusted until FFprobe confirms an audio stream. An HTTP 200 response, a nonempty body, or an `.mp3` extension is not enough; a provider can return other media or opaque data that later fails during playback.

**Why:** A provider returned non-audio data with HTTP 200 and it was cached as an MP3, causing PyTgCalls to reject the file and stop `/play`.

**How to apply:** Validate provider responses and existing cache entries before returning them. Remove invalid cache files and fall back to yt-dlp.

## Hosted YouTube extraction may require provider-first downloads

Direct yt-dlp extraction can be rejected by YouTube's bot challenge in this runtime even when a configured audio provider returns valid audio. Cache misses should use the project's provider-first download path and keep yt-dlp as a fallback.

**Why:** A live cache request hit YouTube's bot challenge through yt-dlp, while the configured provider produced valid audio that was uploaded as PCM.

**How to apply:** Route new cache/download consumers through the existing provider-first path so its provider chain and FFprobe validation are preserved; do not bypass it with direct yt-dlp calls.
