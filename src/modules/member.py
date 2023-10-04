################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# member.py - member management functions and commands

# imports
from re import I
import discord

import discord.ext.commands as commands

import src.module as kiyo_mod



# member module
class KiyokoModule_Member(kiyo_mod.KiyokoModule_Base):
    # Shows a message when a member leaves the guild and the log channel for the "on_member_leave" event
    # is configured and enabled.
    #
    # Returns nothing.
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        # Get respective guild config.
        gcfg = self._app.gcman.getgconfig(member.guild.id)
        
        # If the "on_member_leave" rule is enabled and has a log channel set, log the message.
        if gcfg.logrules['on_member_leave']:
            # Get 'logchan' of guild.
            (enabled, chan) = gcfg.logchan or (False, 0)
            if enabled and chan != 0:
                ch = self._app.get_channel(chan)
                if ch is None:
                    return
                
                # Send leaver message.
                await ch.send(f'Member **{member.display_name}** ({member.name}#{member.discriminator}) has left the server!')
                


# module entrypoint
async def setup(app) -> None:
    # Add 'rules' command to the tree.
    await app.add_cog(KiyokoModule_Member(app))
    

