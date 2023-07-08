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

import src.module as kiyo_mod



# 'member' module class
class KiyokoModule_Member(kiyo_mod.KiyokoModule_Base):
    # Overrides the event that is called whenever a member joins
    # the guild.
    #
    # Returns nothing.
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        pass



# module entrypoint
async def setup(app) -> None:
    await app.add_cog(KiyokoModule_Member(app))


