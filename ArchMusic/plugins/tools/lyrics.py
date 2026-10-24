#
# Copyright (C) 2021-2023 by ArchBots@Github, < https://github.com/ArchBots >.
#
# This file is part of < https://github.com/ArchBots/ArchMusic > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/ArchBots/ArchMusic/blob/master/LICENSE >
#
# All rights reserved.
#

import asyncio
import logging
import random
import re
import string

import aiohttp
from pyrogram import filters
from pyrogram.types import (InlineKeyboardButton,
                            InlineKeyboardMarkup, Message)

from config import BANNED_USERS, lyrical
from strings import get_command
from ArchMusic import app
from ArchMusic.utils.decorators.language import language

###Commands
LYRICS_COMMAND = get_command("LYRICS_COMMAND")
LRCLIB_SEARCH_URL = "https://lrclib.net/api/search"
LRCLIB_USER_AGENT = (
    "ArchMusicBot/1.0 (https://github.com/ArchBots/ArchMusic)"
)
LOGGER = logging.getLogger(__name__)


async def search_lyrics(query: str) -> str | None:
    timeout = aiohttp.ClientTimeout(total=15)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                LRCLIB_SEARCH_URL,
                params={"q": query},
                headers={"User-Agent": LRCLIB_USER_AGENT},
            ) as response:
                if response.status != 200:
                    LOGGER.warning(
                        "LRCLIB lyrics search returned HTTP %s",
                        response.status,
                    )
                    return None
                results = await response.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        LOGGER.warning(
            "LRCLIB lyrics search failed: %s", type(exc).__name__
        )
        return None

    if not isinstance(results, list):
        return None

    for result in results:
        if not isinstance(result, dict):
            continue
        plain_lyrics = result.get("plainLyrics")
        if isinstance(plain_lyrics, str) and plain_lyrics.strip():
            return plain_lyrics.strip()

        synced_lyrics = result.get("syncedLyrics")
        if isinstance(synced_lyrics, str) and synced_lyrics.strip():
            lyrics = re.sub(
                r"\[\d{1,2}:\d{2}(?:\.\d+)?\]",
                "",
                synced_lyrics,
            )
            lyrics = re.sub(
                r"(?im)^\[(?:ar|ti|al|by|re|ve|length|offset):[^\]]*\]\s*",
                "",
                lyrics,
            )
            lyrics = "\n".join(
                line.strip() for line in lyrics.splitlines() if line.strip()
            )
            if lyrics:
                return lyrics
    return None


@app.on_message(
    filters.command(LYRICS_COMMAND) 
    & ~BANNED_USERS
)
@language
async def lrsearch(client, message: Message, _):
    if len(message.command) < 2:
        return await message.reply_text(_["lyrics_1"])
    title = message.text.split(None, 1)[1]
    m = await message.reply_text(_["lyrics_2"])
    lyric = await search_lyrics(title)
    if not lyric:
        return await m.edit(_["lyrics_3"].format(title))
    ran_hash = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=10)
    )
    if "Embed" in lyric:
        lyric = re.sub(r"\d*Embed", "", lyric)
    lyrical[ran_hash] = lyric
    upl = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=_["L_B_1"],
                    url=f"https://t.me/{app.username}?start=lyrics_{ran_hash}",
                ),
            ]
        ]
    )
    await m.edit(_["lyrics_4"], reply_markup=upl)
