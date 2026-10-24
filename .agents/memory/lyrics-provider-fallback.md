---
name: Lyrics provider fallback
description: The Genius public search endpoint returned HTTP 403 from this bot environment.
---

Genius search through LyricsGenius' public endpoint returned a 403 HTML challenge in the bot environment. LRCLIB's identified, unauthenticated search endpoint returned lyrics for the same title and supports both plain and timestamped results.

**Why:** The Genius error escaped the `/lyrics` handler and produced a Pyrogram dispatcher traceback, while the alternative provider returned usable results without credentials.

**How to apply:** Keep `/lyrics` resilient to external-provider failures, send a descriptive `User-Agent` to LRCLIB, and strip timestamps when a record only contains synced lyrics. Do not put provider tokens in source code.
