---
name: YouTube search/httpx compatibility
description: Known httpx version constraint for the project's YouTube search dependency.
---

`youtube-search-python` 1.6.6 passes the `proxies` argument to `httpx.AsyncClient`; `httpx` 0.28 removed that argument. Keep the project pinned to `httpx==0.27.2` unless the search library is upgraded or replaced.

**Why:** `/play` caught the resulting `TypeError` and displayed the generic “Failed to process query” message. The exact query worked after pinning httpx 0.27.2.

**How to apply:** When changing YouTube search dependencies, verify `VideosSearch` with an actual query and keep the httpx pin until the calling library no longer uses `proxies=`.
