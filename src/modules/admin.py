################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# admin.py - commands for administration of the bot

# imports
import discord, time
import discord.app_commands as app_commands
import discord.ext.commands as commands

import src.module as kiyo_mod



# class representing the 'admin' Cog
class KiyokoModule_Admin(kiyo_mod.KiyokoModule_Base):
    # This command syncs the command tree (either guild-specific
    # or global) to Discord. Use it whenever a command has been
    # added/removed. Note that this command can only be used by
    # the bot's owner.
    #
    # Returns nothing.
    @commands.command(name = 'sync')
    @commands.check(commands.is_owner())
    async def cmd_sync(self, ctx: commands.Context) -> None:
        # Sync command tree.
        self._app.tree.copy_global_to(guild = ctx.guild)
        res = await self._app.tree.sync(guild = ctx.guild)

        # Send response.
        await ctx.send(f'Successfully synched {len(res)} commands to guild \'{ctx.guild.name}\'.')


    # This handler handles command errors.
    #
    # Returns nothing.
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, err) -> None:
        # Fetch required data.
        tnow   = time.strftime('%I:%M:%S %p', time.localtime())
        errcap = 'Detailed Description: '

        # Create basic embed.
        embed = discord.Embed(
            title       = ':no_entry_sign: Command Error',
            description = f'While processing command \'{ctx.invoked_with}\', an error occurred. Use /help to view a list of all available commands and to get more information regarding a specific command.',
            color       = discord.Color(0xFF4646)
        )
        embed.set_footer(text = f'Issued by {ctx.author.display_name} at {tnow}', icon_url = ctx.author.display_avatar.url)
        embed.add_field(name = errcap, value = None, inline=False)

        # Extend embed with more information on command error.
        match err:
            # Command could not be found.
            case commands.CommandNotFound():
                embed.set_field_at(0, name = errcap, value = 'Command not found. Check spelling and use /help if in doubt.')

        # Send embed containing error information.
        await ctx.send(embed = embed)



# module entrypoint
async def setup(app) -> None:
    await app.add_cog(KiyokoModule_Admin(app))


