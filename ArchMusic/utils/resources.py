import os
import shutil

import psutil

from ArchMusic.logging import LOGGER

logger = LOGGER(__name__)

try:
    MAX_ACTIVE_VC = max(1, int(os.getenv("MAX_ACTIVE_VC", "8")))
except (TypeError, ValueError):
    MAX_ACTIVE_VC = 8

VOICE_CHAT_REFUSE_RATIO = 0.88


def _read_cgroup_integer(paths):
    for path in paths:
        try:
            with open(path, encoding="ascii") as value_file:
                value = value_file.read().strip()
            if value.lower() == "max":
                continue
            value = int(value)
            if 0 < value < (1 << 60):
                return value
        except (OSError, ValueError):
            continue
    return None


def _memory_snapshot():
    try:
        rss_bytes = psutil.Process(os.getpid()).memory_info().rss
    except (psutil.Error, OSError):
        rss_bytes = 0

    memory_limit = _read_cgroup_integer(
        (
            "/sys/fs/cgroup/memory.max",
            "/sys/fs/cgroup/memory/memory.limit_in_bytes",
        )
    )
    cgroup_usage = _read_cgroup_integer(
        (
            "/sys/fs/cgroup/memory.current",
            "/sys/fs/cgroup/memory/memory.usage_in_bytes",
        )
    )
    if memory_limit is None:
        memory_limit = 512 * 1024**2
    measured_bytes = cgroup_usage or rss_bytes
    return rss_bytes, measured_bytes, memory_limit, measured_bytes / memory_limit


def memory_pressure_high():
    return _memory_snapshot()[3] > 0.75


async def _active_vc_count():
    from ArchMusic.utils.database import get_active_chats

    active_chats = await get_active_chats()
    return len(active_chats or ())


async def voice_chat_admission_error(chat_id):
    """Return a refusal only when this chat would start a new voice call."""
    from ArchMusic.utils.database import is_active_chat

    try:
        if await is_active_chat(chat_id):
            return None
    except Exception:
        logger.warning(
            "Could not determine whether chat %s is already active", chat_id
        )

    if _memory_snapshot()[3] >= VOICE_CHAT_REFUSE_RATIO:
        return "Bot is busy, try again in a minute."
    try:
        active_vcs = await _active_vc_count()
    except Exception:
        logger.warning("Could not count active voice chats for admission")
        return None
    if active_vcs >= MAX_ACTIVE_VC:
        return "Bot is busy, try again in a minute."
    return None


def _ffmpeg_process_count():
    count = 0
    for process in psutil.process_iter(["name", "cmdline"]):
        try:
            name = (process.info.get("name") or "").lower()
            command = process.info.get("cmdline") or []
            executable = os.path.basename(command[0]).lower() if command else ""
            if name.startswith("ffmpeg") or executable.startswith("ffmpeg"):
                count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return count


async def resource_snapshot():
    rss, measured, limit, ratio = _memory_snapshot()
    try:
        active_vcs = await _active_vc_count()
    except Exception:
        active_vcs = "unknown"
    try:
        free_tmp_bytes = shutil.disk_usage("/tmp").free
    except OSError:
        free_tmp_bytes = None
    ffmpeg_processes = _ffmpeg_process_count()
    orphan_processes = (
        max(0, ffmpeg_processes - active_vcs)
        if isinstance(active_vcs, int)
        else None
    )
    return {
        "active_vcs": active_vcs,
        "rss_bytes": rss,
        "measured_bytes": measured,
        "limit_bytes": limit,
        "ratio": ratio,
        "free_tmp_bytes": free_tmp_bytes,
        "ffmpeg_processes": ffmpeg_processes,
        "orphan_ffmpeg_processes": orphan_processes,
    }
