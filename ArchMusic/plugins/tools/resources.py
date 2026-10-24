from pyrogram import filters

import config
from ArchMusic import app
from ArchMusic.utils.resources import resource_snapshot


@app.on_message(filters.command("botload") & filters.user(config.OWNER_ID))
async def show_bot_load(_, message):
    try:
        load = await resource_snapshot()
    except Exception:
        return await message.reply_text("Unable to read bot resource usage.")

    ratio = load["ratio"] * 100
    limit_mib = load["limit_bytes"] / (1024**2)
    tmp_free = load["free_tmp_bytes"]
    tmp_text = (
        f"{tmp_free / (1024**3):.2f} GiB"
        if tmp_free is not None
        else "unavailable"
    )
    orphan_text = (
        str(load["orphan_ffmpeg_processes"])
        if load["orphan_ffmpeg_processes"] is not None
        else "unavailable"
    )
    await message.reply_text(
        "Bot load\n"
        f"Active voice chats: {load['active_vcs']}\n"
        f"Memory: {load['rss_bytes'] / (1024**2):.0f} MiB RSS "
        f"(container {ratio:.1f}% of {limit_mib:.0f} MiB)\n"
        f"FFmpeg processes: {load['ffmpeg_processes']} "
        f"(orphan estimate: {orphan_text})\n"
        f"Free /tmp: {tmp_text}"
    )
