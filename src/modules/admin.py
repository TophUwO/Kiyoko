################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# admin.py - commands for administration of the bot

# imports
import discord

from typing               import Optional
from discord.app_commands import *

import src.modules.guild as kiyo_guild
import src.utils         as kiyo_utils
import src.error         as kiyo_error



# command group representing the /config command
@discord.app_commands.default_permissions(administrator = True)
@discord.app_commands.guild_only()
class KiyokoCommandGroup_Config(discord.app_commands.Group):
    def __init__(self, app, name: str, desc: str):
        super().__init__(name = name, description = desc)

        self._app = app

    
    # Configures the 'logchan' item which controls the channel that logging messages
    # of the application will be sent to. The application needs to be able to send messages
    # in this channel.
    #
    # Returns nothing.
    @discord.app_commands.command(name = 'logchan', description = 'configures the logging channel the application will use')
    @discord.app_commands.describe(
        enabled = 'whether or not logging to the logging channel is enabled',
        channel = 'channel to use for logging; preferably a private, staff-only channel'
    )
    @discord.app_commands.guild_only()
    @discord.app_commands.checks.has_permissions(administrator = True)
    @discord.app_commands.check(kiyo_utils.isenabled)
    @discord.app_commands.check(kiyo_utils.updcmdstats)
    async def cmd_logchan(self, inter: discord.Interaction, enabled: Optional[bool], channel: Optional[discord.TextChannel]) -> None:
        # If the given channel is not None, check if the bot has all required permissions there.
        if channel is not None:
            reqperms = discord.Permissions(view_channel = True, embed_links = True, send_messages = True)
            if not kiyo_utils.haschanperms(inter, channel, reqperms):
                raise kiyo_error.MissingChannelPermissions

        # If the entry does not exist in the guild config object, create it.
        gcfg = self._app.gcman.getgconfig(inter.guild_id)
        if gcfg.logchan is None:
            gcfg.logchan = (False, 0)

        # Update guild config cache.
        olden   = gcfg.logchan[0]
        oldchan = gcfg.logchan[1]
        gcfg.logchan = (
            gcfg.logchan[0] if enabled is None else enabled,
            gcfg.logchan[1] if channel is None else channel.id
        )
        # Update configuration in database.
        await kiyo_guild.updgsettings(self._app, gcfg)

        # Prepare and send response.
        (embed, file) = kiyo_utils.cfgupdembed(
            inter = inter,
            desc  = 'logchan',
            upd   = [
                ('enabled', olden,   gcfg.logchan[0]) if enabled is not None and olden   != gcfg.logchan[0] else None,
                ('channel', oldchan, gcfg.logchan[1]) if channel is not None and oldchan != gcfg.logchan[1] else None
            ]
        )
        await kiyo_utils.sendmsgsecure(inter, embed = embed, file = file)



# module entrypoint
async def setup(app) -> None:
    # Register '/config' command and all of its sub-commands.
    app.tree.add_command(
        KiyokoCommandGroup_Config(
            app,
            name = 'config',
            desc = 'get and/or update guild-wide general configuration options'
        )
    )


