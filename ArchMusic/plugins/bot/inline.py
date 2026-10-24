#
# Copyright (C) 2021-2023 by ArchBots@Github, < https://github.com/ArchBots >.
#
# This file is part of < https://github.com/ArchBots/ArchMusic > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/ArchBots/ArchMusic/blob/master/LICENSE >
#
# All rights reserved.
#

from pyrogram.types import (InlineKeyboardButton,
                            InlineKeyboardMarkup,
                            InlineQueryResultArticle,
                            InlineQueryResultPhoto,
                            InputTextMessageContent)
from youtubesearchpython.__future__ import VideosSearch

from config import BANNED_USERS, MUSIC_BOT_NAME
from ArchMusic import app
from ArchMusic.logging import LOGGER
from ArchMusic.utils.inlinequery import answer


@app.on_inline_query(~BANNED_USERS)
async def inline_query_handler(client, query):
    text = (query.query or "").strip()
    if not text:
        results = answer
    else:
        try:
            response = await VideosSearch(text, limit=20).next()
            videos = (response or {}).get("result") or []
        except Exception:
            LOGGER(__name__).exception("Inline YouTube search failed")
            videos = None

        if videos is None:
            results = [
                InlineQueryResultArticle(
                    title="Search temporarily unavailable",
                    description="Please try this search again shortly.",
                    input_message_content=InputTextMessageContent(
                        "Inline search is temporarily unavailable. Please try again shortly."
                    ),
                )
            ]
        elif not videos:
            results = [
                InlineQueryResultArticle(
                    title="No videos found",
                    description="Try a different search query.",
                    input_message_content=InputTextMessageContent(
                        "No videos were found for that search."
                    ),
                )
            ]
        else:
            results = []
            for video in videos[:15]:
                try:
                    title = (video.get("title") or "Untitled video").title()
                    duration = video.get("duration") or "Unknown"
                    views = (video.get("viewCount") or {}).get("short") or "Unknown"
                    thumbnails = video.get("thumbnails") or []
                    thumbnail_url = thumbnails[0].get("url") if thumbnails else None
                    channel_info = video.get("channel") or {}
                    channellink = channel_info.get("link")
                    channel = channel_info.get("name") or "Unknown"
                    link = video.get("link")
                    published = video.get("publishedTime") or "Unknown"

                    if not thumbnail_url or not link:
                        continue

                    thumbnail = thumbnail_url.split("?")[0]
                    description = (
                        f"{views} | {duration} | {channel} | {published}"
                    )
                    buttons = InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    text="🎥 Watch on Youtube",
                                    url=link,
                                )
                            ],
                        ]
                    )
                    channel_line = (
                        f"📎**Channel Link:** [Visit From Here]({channellink})"
                        if channellink
                        else f"🎥**Channel Name:** {channel}"
                    )
                    searched_text = f"""
❇️**Title:** [{title}]({link})

⏳**Duration:** {duration} Mins
👀**Views:** `{views}`
⏰**Published Time:** {published}
🎥**Channel Name:** {channel}
{channel_line}

__Reply with /play on this searched message to stream it on voice chat.__

⚡️ ** Inline Search By {MUSIC_BOT_NAME} **"""
                    results.append(
                        InlineQueryResultPhoto(
                            photo_url=thumbnail,
                            title=title,
                            thumb_url=thumbnail,
                            description=description,
                            caption=searched_text,
                            reply_markup=buttons,
                        )
                    )
                except Exception:
                    LOGGER(__name__).exception(
                        "Skipping an incomplete inline YouTube result"
                    )

            if not results:
                results = [
                    InlineQueryResultArticle(
                        title="No usable videos found",
                        description="Try a different search query.",
                        input_message_content=InputTextMessageContent(
                            "No usable videos were found for that search."
                        ),
                    )
                ]

    try:
        return await client.answer_inline_query(
            query.id, results=results, cache_time=10
        )
    except Exception:
        LOGGER(__name__).exception("Failed to answer an inline query")
