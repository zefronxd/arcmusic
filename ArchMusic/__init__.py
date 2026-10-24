#
# Copyright (C) 2021-2023 by ArchBots@Github, < https://github.com/ArchBots >.
#
# This file is part of < https://github.com/ArchBots/ArchMusic > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/ArchBots/ArchMusic/blob/master/LICENSE >
#
# All rights reserved.
#

# Pyrogram 2.0.106 still caps channel IDs at the older 32-bit range.
# Extend its channel range to the library's supported maximum before clients
# are created so newer Telegram supergroups can be resolved during updates.
from pyrogram import utils as pyrogram_utils

pyrogram_utils.MIN_CHANNEL_ID = min(
    pyrogram_utils.MIN_CHANNEL_ID,
    pyrogram_utils.MAX_CHANNEL_ID - pyrogram_utils.MAX_USER_ID,
)

from ArchMusic.core.bot import ArchMusic
from ArchMusic.core.dir import dirr
from ArchMusic.core.git import git
from ArchMusic.misc import dbb, heroku, sudo

from .logging import LOGGER

# Directories
dirr()

# Check Git Updates
git()

# Initialize Memory DB
dbb()

# Heroku APP
heroku()

# Load Sudo Users from DB
sudo()

# Bot Client
app = ArchMusic()

# Assistant Client
from ArchMusic.core.userbot import Userbot

userbot = Userbot()

from .platforms import *

YouTube = YouTubeAPI()
Carbon = CarbonAPI()
Spotify = SpotifyAPI()
Apple = AppleAPI()
Resso = RessoAPI()
SoundCloud = SoundAPI()
Telegram = TeleAPI()
