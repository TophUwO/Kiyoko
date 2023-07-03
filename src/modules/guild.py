################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# guild.py - event handlers and commands meant for guild management

# imports
import discord
import discord.app_commands as app_commands
import discord.ext.commands as commands
from loguru import logger

import src.app    as kiyo_app
import src.module as kiyo_mod


# Cog defining guild-related functionality
class KiyokoModule_Guild(kiyo_mod.KiyokoModule_Base):
    # This event is executed when the bot joins a guild. This can happen whenever the
    # bot is invited to join the guild or the bot creates a guild.
    #
    # Returns nothing.
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        logger.info(f'Joined guild \'{guild.name}\' (id: {guild.id}).')

    # Temporary test command.
    @app_commands.command(name='test')
    async def cmd_test(self, interaction: discord.Interaction) -> None:
        logger.info('Command executed.')
        await interaction.response.send_message('Executed test command.')


# module entrypoint
async def setup(app: kiyo_app.KiyokoApplication) -> None:
    await app.add_cog(KiyokoModule_Guild(app))


