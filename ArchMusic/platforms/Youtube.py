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
import os
import re
from urllib.parse import parse_qs, urlparse
from typing import Union

import aiofiles
import aiohttp
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

import config
from ArchMusic.utils.database import is_on_off
from ArchMusic.utils.formatters import time_to_seconds


API_URL = (
    os.environ.get("ApiUrl")
    or os.environ.get("SHRUTI_API_URL")
    or "https://api.shrutibots.site"
).rstrip("/")
SHRUTI_API_KEY = (
    os.environ.get("SHRUTI_API_KEY")
    or os.environ.get("APIKey")
    or ""
)
ZEFRON_API_KEY = os.environ.get("ZEFRON_API_KEY", "")
YUKI_API_KEY = os.environ.get("YUKI_API_KEY", "")
YUKI_STREAM_URL = "https://music.yukiapi.site/stream"
DOWNLOAD_DIR = "downloads"
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(4)


def _video_id(link: str) -> str:
    value = str(link or "").strip()
    if "://" not in value:
        return value.split("&", 1)[0]

    parsed = urlparse(value)
    if parsed.hostname == "youtu.be":
        return parsed.path.strip("/").split("/", 1)[0]
    return parse_qs(parsed.query).get("v", [""])[0]


async def _has_audio_stream(path: str) -> bool:
    if not path or not os.path.isfile(path):
        return False

    try:
        process = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            output, _ = await asyncio.wait_for(
                process.communicate(), timeout=30
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            return False
        return process.returncode == 0 and output.strip() == b"audio"
    except OSError:
        return False


async def _download_provider(
    session,
    url: str,
    params: dict,
    path: str,
    total_timeout: int,
    fast_timeout: int = 0,
) -> bool:
    temp_path = f"{path}.part"
    timeout = aiohttp.ClientTimeout(
        total=total_timeout,
        connect=fast_timeout or 30,
        sock_connect=fast_timeout or 30,
        sock_read=fast_timeout or 60,
    )
    try:
        async with session.get(url, params=params, timeout=timeout) as response:
            if response.status != 200:
                return False
            content_type = response.headers.get("Content-Type", "").lower()
            if (
                "json" in content_type
                or content_type.startswith("text/")
                or content_type.startswith("video/")
            ):
                return False
            async with aiofiles.open(temp_path, "wb") as output:
                async for chunk in response.content.iter_chunked(131072):
                    await output.write(chunk)

        if (
            os.path.getsize(temp_path) > 0
            and await _has_audio_stream(temp_path)
        ):
            os.replace(temp_path, path)
            return True
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
        pass
    finally:
        if os.path.exists(temp_path):
            try:
                await asyncio.to_thread(os.remove, temp_path)
            except OSError:
                pass
    return False


async def _download_unlimited(link: str) -> str | None:
    video_id = _video_id(link)
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,64}", video_id):
        return None

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")
    if os.path.exists(path):
        if await _has_audio_stream(path):
            return path
        try:
            await asyncio.to_thread(os.remove, path)
        except OSError:
            return None

    sources = []
    if ZEFRON_API_KEY:
        sources.append(
            (
                "https://zefronapi.me/download",
                {
                    "api_key": ZEFRON_API_KEY,
                    "type": "audio",
                    "url": video_id,
                },
                4,
            )
        )
    if YUKI_API_KEY:
        sources.append(
            (
                f"{YUKI_STREAM_URL}/{video_id}",
                {"key": YUKI_API_KEY, "type": "audio"},
                0,
            )
        )
    if SHRUTI_API_KEY:
        endpoint = (
            API_URL
            if API_URL.endswith("/download")
            else f"{API_URL}/download"
        )
        sources.append(
            (
                endpoint,
                {
                    "url": video_id,
                    "type": "audio",
                    "api_key": SHRUTI_API_KEY,
                },
                0,
            )
        )

    async with aiohttp.ClientSession() as session:
        for url, params, fast_timeout in sources:
            if await _download_provider(
                session, url, params, path, 300, fast_timeout
            ):
                return path
    return None


async def download_song(link: str) -> str | None:
    async with DOWNLOAD_SEMAPHORE:
        return await _download_unlimited(link)


async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if (
            "unavailable videos are hidden"
            in (errorz.decode("utf-8")).lower()
        ):
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(
            r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
        )

    async def exists(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if re.search(self.regex, link):
            return True
        else:
            return False

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

    async def details(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            if str(duration_min) == "None":
                duration_sec = 0
            else:
                duration_sec = int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
        return title

    async def duration(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            duration = result["duration"]
        return duration

    async def thumbnail(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        return thumbnail

    async def video(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "-g",
            "-f",
            "best[height<=?720][width<=?1280]",
            f"{link}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        else:
            return 0, stderr.decode()

    async def playlist(
        self, link, limit, user_id, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        playlist = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
        )
        try:
            result = playlist.split("\n")
            for key in result:
                if key == "":
                    result.remove(key)
        except:
            result = []
        return result

    async def track(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }
        return track_details, vidid

    async def formats(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        ytdl_opts = {"quiet": True}
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r["formats"]:
                try:
                    str(format["format"])
                except:
                    continue
                if not "dash" in str(format["format"]).lower():
                    try:
                        format["format"]
                        format["filesize"]
                        format["format_id"]
                        format["ext"]
                        format["format_note"]
                    except:
                        continue
                    formats_available.append(
                        {
                            "format": format["format"],
                            "filesize": format["filesize"],
                            "format_id": format["format_id"],
                            "ext": format["ext"],
                            "format_note": format["format_note"],
                            "yturl": link,
                        }
                    )
        return formats_available, link

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split(
            "?"
        )[0]
        return title, duration_min, thumbnail, vidid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> tuple[str | None, bool] | str | None:
        if videoid:
            link = self.base + link
        loop = asyncio.get_running_loop()

        def audio_dl():
            ydl_optssx = {
                "format": "bestaudio",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = os.path.join(
                "downloads", f"{info['id']}.{info['ext']}"
            )
            if os.path.exists(xyz):
                return xyz
            x.download([link])
            return xyz

        def video_dl():
            ydl_optssx = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = os.path.join(
                "downloads", f"{info['id']}.{info['ext']}"
            )
            if os.path.exists(xyz):
                return xyz
            x.download([link])
            return xyz

        def song_video_dl():
            formats = f"{format_id}+140"
            fpath = f"downloads/{title}"
            ydl_optssx = {
                "format": formats,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])

        def song_audio_dl():
            fpath = f"downloads/{title}.%(ext)s"
            ydl_optssx = {
                "format": format_id,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])

        if songvideo:
            await loop.run_in_executor(None, song_video_dl)
            fpath = f"downloads/{title}.mp4"
            return fpath
        elif songaudio:
            await loop.run_in_executor(None, song_audio_dl)
            fpath = f"downloads/{title}.mp3"
            return fpath
        elif video:
            if await is_on_off(config.YTDOWNLOADER):
                direct = True
                downloaded_file = await loop.run_in_executor(
                    None, video_dl
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    "yt-dlp",
                    "-g",
                    "-f",
                    "best[height<=?720][width<=?1280]",
                    f"{link}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if stdout:
                    downloaded_file = stdout.decode().split("\n")[0]
                    direct = None
                else:
                    return
        else:
            direct = True
            downloaded_file = await download_song(link)
            if not downloaded_file:
                downloaded_file = await loop.run_in_executor(
                    None, audio_dl
                )
                if not await _has_audio_stream(downloaded_file):
                    if downloaded_file and os.path.isfile(downloaded_file):
                        try:
                            await asyncio.to_thread(
                                os.remove, downloaded_file
                            )
                        except OSError:
                            pass
                    downloaded_file = await loop.run_in_executor(
                        None, audio_dl
                    )
                    if not await _has_audio_stream(downloaded_file):
                        raise RuntimeError(
                            "yt-dlp did not produce a valid audio stream"
                        )
        return downloaded_file, direct
