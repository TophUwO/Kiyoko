################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# member.py - event handlers and commands dedicated to member management

# imports
import discord
import discord.ext.commands as commands
from loguru import logger

import src.app as kiyo_app



# 'member' module class
class KiyokoModule_Member(commands.Cog):
    def __init__(self, app: kiyo_app.KiyokoApplication):
        self._app = app


    # Overrides the event that is called whenever a member joins
    # the guild.
    #
    # Returns nothing.
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        # Check if welcome channel is configured and the setting is enabled.
        chanid = int(self._app.gcfg[member.guild.id].welcomechan)
        if chanid is None:
            logger.warning(f'Welcome channel for guild "{member.guild.name}" (id: {member.guild.id}) is not configured.')

            return

        # Get welcome channel by id and send welcome message.
        chan = member.guild.get_channel(chanid)
        user = self._app.get_user(member.id)
        await chan.send(f'Welcome to *{member.guild.name}*, **{user.name}**!')



# module entrypoint
async def setup(app: kiyo_app.KiyokoApplication) -> None:
    await app.add_cog(KiyokoModule_Member(app))


