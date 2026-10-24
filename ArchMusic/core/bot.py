import sys

import aiohttp
from pyrogram import Client
from pyrogram.types import BotCommand

import config

from ..logging import LOGGER


class ArchMusic(Client):
    def __init__(self):
        LOGGER(__name__).info(f"Starting Bot")
        super().__init__(
            "ArchMusic",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
        )

    async def start(self):
        await super().start()
        try:
            get_me = await self.get_me()
            self.username = get_me.username
            self.id = get_me.id

            video_url = "https://telegra.ph/file/36221d40afde82941ffff.mp4"
            caption = "Bot Started"

            try:
                await self._bot_api(
                    "sendVideo",
                    {
                        "chat_id": config.LOG_GROUP_ID,
                        "video": video_url,
                        "caption": caption,
                    },
                )
            except Exception as e:
                error = str(e)
                if config.BOT_TOKEN:
                    error = error.replace(config.BOT_TOKEN, "[redacted]")
                LOGGER(__name__).error(
                    "Bot could not post its startup message to the log group. "
                    f"Check the configured group ID and bot permissions. Error: {error}"
                )
                sys.exit()

            if config.SET_CMDS == str(True):
                try:
                    await self.set_bot_commands(
                        [
                            BotCommand("ping", "Check that bot is alive or dead"),
                            BotCommand("play", "Starts playing the requested song"),
                            BotCommand("botload", "Shows bot memory and voice-chat load"),
                            BotCommand("skip", "Moves to the next track in queue"),
                            BotCommand("pause", "Pause the current playing song"),
                            BotCommand("resume", "Resume the paused song"),
                            BotCommand("end", "Clear the queue and leave voice chat"),
                            BotCommand("shuffle", "Randomly shuffles the queued playlist."),
                            BotCommand("playmode", "Allows you to change the default playmode for your chat"),
                            BotCommand("settings", "Open the settings of the music bot for your chat.")
                        ]
                    )
                except:
                    pass
            else:
                pass

            member = await self._bot_api(
                "getChatMember",
                {
                    "chat_id": config.LOG_GROUP_ID,
                    "user_id": self.id,
                },
            )
            if member.get("status") not in ("administrator", "creator"):
                LOGGER(__name__).error(
                    "Please promote Bot as Admin in Logger Group"
                )
                sys.exit()

        except Exception as e:
            LOGGER(__name__).error(f"Error during bot start: {e}")
            sys.exit()

        if get_me.last_name:
            self.name = get_me.first_name + " " + get_me.last_name
        else:
            self.name = get_me.first_name

        LOGGER(__name__).info(f"MusicBot Started as {self.name}")

    @staticmethod
    async def _bot_api(method, payload):
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/{method}"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json(content_type=None)
                if response.status != 200 or not result.get("ok"):
                    description = result.get("description", "unknown error")
                    raise RuntimeError(
                        f"Telegram Bot API {method} failed: {description}"
                    )
                return result["result"]
