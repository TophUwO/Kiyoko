################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# help.py - interactive help command, utilizing GUI

# imports
import discord, discord.ui

from typing import Optional

import src.module as kiyo_mod
import src.error  as kiyo_error



# class holding the '/help' command
class KiyokoModule_Help(kiyo_mod.KiyokoModule_Base):
    # Implements an interactive help command, featuring advanced filter options, in-depth
    # explanations and controls via GUI.
    #
    # Returns nothing.
    @discord.app_commands.command(name = 'help', description = 'interactive help command')
    @discord.app_commands.describe(
        commands = 'name(s) of the specific command(s) to show the help page of; comma-separated',
        filters  = 'filters(s) to apply to the command listing; comma-separated',
        overview = 'whether to show a brief overview or a detailed page for every command; True by default'
    )
    async def cmd_help(self, inter: discord.Interaction, commands: Optional[str], filters: Optional[str], overview: Optional[bool]) -> None:
        raise kiyo_error.AppCmd_NotImplemented



# module entrypoint
async def setup(app) -> None:
    await app.add_cog(KiyokoModule_Help(app))


