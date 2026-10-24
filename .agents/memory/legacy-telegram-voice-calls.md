---
name: Legacy Telegram voice calls
description: Compatibility constraints for this bot's older PyTgCalls streaming interface.
---

This bot's call implementation depends on the legacy PyTgCalls stream types and module paths; the compatible runtime is PyTgCalls 1.0.9 with ntgcalls 1.0.2. In this PyTgCalls version, `join_group_call` does not accept a `stream_type` keyword; infer the stream from the `AudioPiped`/`AudioVideoPiped` object. Motor 3.2.0 also requires an older PyMongo 4.x build; the compatible pin used here is PyMongo 4.5.0. Pyrogram 2.0.106 has a stale 32-bit channel-ID lower bound, so startup expands `MIN_CHANNEL_ID` using its `MAX_USER_ID` before creating clients.

**Why:** Unpinned installs select newer releases whose APIs or internal imports are incompatible with this older call and database code, preventing startup. Passing `stream_type` to the pinned `join_group_call` raises `TypeError` and stops playback after search. The Pyrogram range adjustment avoids background update-handler failures for newer Telegram channels without replacing the client library used by the legacy calls stack.

**How to apply:** Keep these dependency pairs aligned when changing requirements and inspect the installed `join_group_call` signature before copying arguments from other PyTgCalls versions. Preserve the early Pyrogram range adjustment unless a client upgrade fixes the bounds; validate large channel IDs and voice playback together before changing the Telegram client stack.
