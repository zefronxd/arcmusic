# Running ArchMusic on Replit

This is a Python Telegram music bot, not a web application. Use the existing
**Run Telegram bot** workflow (or the Run button). Output appears in the console.

## Runtime

- Python 3.12 and FFmpeg are configured in `.replit`.
- Python dependencies are listed in `requirements.txt`.
- Keep the legacy PyTgCalls/ntgcalls and Motor/PyMongo version pairs aligned.

## Secrets

Configure credentials only in Replit Secrets, never in source files:

- `API_ID`, `API_HASH`: Telegram application credentials.
- `TOKEN`: Telegram bot token.
- `MONGO_URI`: MongoDB connection URI.
- `LOGGER_ID`: Logger supergroup ID.
- `STRING1`: Assistant-account Pyrogram session string.
- `OWNER_ID`: Bot owner's Telegram user ID.
- `SONG_DURATION_LIMIT`: Download duration limit in minutes.

The workflow maps `TOKEN`, `MONGO_URI`, `LOGGER_ID`, `STRING1`, and
`SONG_DURATION_LIMIT` to the environment variable names expected by the bot,
then runs `python3 -m ArchMusic`.

## Telegram prerequisites

1. Add the bot to the logger supergroup and promote it to administrator.
2. Add the assistant account represented by `STRING1` to that group.
3. Start a voice chat in the logger group and keep it running.
4. Start the workflow. Successful full startup logs
   `Arch Music Bot Started Successfully`.

The bot posts its startup message and checks its administrator status through
the Telegram Bot API, which does not depend on Pyrogram's per-session peer
cache. Assistant user sessions load their dialog list before addressing the
private logger group by numeric ID, so a fresh session can resolve its access
hash.

Spotify queries require the optional `SPOTIFY_CLIENT_ID` and
`SPOTIFY_CLIENT_SECRET`; their absence does not prevent basic startup.

## Setup verification

Dependencies installed successfully and `python3 -m pip check` passed.
The earlier startup failed on Pyrogram's missing private-group peer cache.
The startup path has been updated to avoid that failure; full Telegram startup
and voice playback still require a workflow run. No website or HTTP port is
expected.
