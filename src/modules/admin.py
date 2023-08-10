################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# admin.py - commands for administration of the bot

# imports
import discord, datetime, enum

from loguru import logger
from typing import Optional

import discord.ext.commands as commands

import src.module        as kiyo_mod
import src.modules.guild as kiyo_guild



# Provides a more convenient way of building an embed to remove boilerplate code.
#
# Returns generated embed object.
def fmtembed(*, color: int, title: str, desc: str, fields: Optional[list[tuple[str, any, bool]]], footer = Optional[tuple[str, any]], thumb: Optional[str]) -> discord.Embed:
    # Prepare embed object.
    res = discord.Embed(
        color       = color,
        title       = title,
        timestamp   = datetime.datetime.now(),
        description = desc
    )
    if footer is not None:
        res.set_footer(text = footer[0], icon_url = footer[1])
    if thumb is not None:
        res.set_thumbnail(url = thumb)

    # Add fields.
    if fields is not None:
        for field in fields:
            if field is None:
                continue

            res.add_field(name = field[0], value = field[1], inline = field[2])

    # Finally, return object.
    return res



# enum holding all application command error codes
class KiyokoAppCommandError(enum.Enum):
    INVSUBCMD    = 'Invalid application sub-command!'                               # invalid sub command
    INVPARAM     = 'Invalid application command parameter!'                         # invalid parameter
    MISSINGPARAM = 'Missing required application command parameter!'                # missing but required parameter
    UINSUFFPERMS = 'Insufficient user permissions for running this command!'        # insufficient invoker permissions
    AINSUFFPERMS = 'Insufficient application permissions for running this command!' # insufficient application permissions
    INVEXECCTX   = 'Invalid execution context!'                                     # invalid execution context (e.g. guild vs pm)


# Call this function in case of an application command error.
# Sends a fancy embed describing the error in detail.
# 
# Returns nothing.
async def cmderrembed(app, *, inter: discord.Interaction, cmd: str, type: KiyokoAppCommandError, desc: str) -> None:
    # Get thumbnail from local file.
    file = discord.File(app.resman.getresource('error').url, filename = 'error.png')

    # Generate fancy explanatory embed.
    embed = fmtembed(
        color  = 0xFF3030,
        title  = 'Application Command Error',
        desc   = f'While processing command ``{cmd}``, an error occurred! Please use ``/help {cmd}`` for detailed usage of this command.',
        fields = [
            ('Error', type.value, True),
            ('Description', desc, True) if desc is not None and desc != '' else None
        ],
        footer = (f'Issued by {inter.user.display_name}', inter.user.display_avatar),
        thumb  = 'attachment://error.png'
    )

    # Send embed message.
    await inter.response.send_message(file = file, embed = embed, ephemeral = True)


# Call this function to send a generic embed in response of a /config command
# execution.
#
# Returns nothing.
async def cfgupdembed(app, *, inter: discord.Interaction, desc: str, upd: list[tuple[str, any, any]]) -> None:
    # Get thumbnail from local file.
    file = discord.File(app.resman.getresource('settings').url, filename = 'settings.png')

    # Get clean list, without possible 'None' items.
    clupd = [x for x in upd if x is not None]

    # Format update info field.
    appendix = ''
    contdata = bool(len(clupd) > 0)
    if contdata:
        # Get length of longest key and longest old setting rep.
        lkey = max([len(str(x[0])) for x in clupd])
        lpre = max([len(str(x[1])) for x in clupd])

        # Use coffeescript for a few fancy colors.
        appendix = '\n\n**__Updated Settings:__**\n```coffeescript'
        for field in [x for x in upd if x is not None]:
            # Calculate necessary padding.
            pad1 = (lkey - len(str(field[0]))) * ' '
            pad2 = (lpre - len(str(field[1]))) * ' '

            # Append line.
            appendix += f'\n{field[0]}{pad1} =-> "{field[1]}"{pad2} => "{field[2]}"'
        appendix += '\n```'
    else:
        # Show a message explaining that nothing had to be updated.
        appendix = '\n\n**Nothing to update!**'

    # Prepare embed.
    embed = fmtembed(
        color  = 0x11ffe8,
        title  = 'Guild Configuration Update',
        desc   = f'Updated guild settings for ``{desc}``. Please note that some settings may take some time'
                  ' (i.e. until the next update of the module that uses the setting) until the changes take effect.' + appendix,
        fields = [],
        footer = (f'Issued by {inter.user.display_name}', inter.user.display_avatar),
        thumb  = 'attachment://settings.png'
    )

    # Send embed.
    await inter.response.send_message(file = file, embed = embed)


# Checks if the user has at least a set of required privileges and if not, displays
# a permission error.
#
# Returns nothing.
async def helper_hasperms(app, cmd: str, inter: discord.Interaction, user: discord.User, perms: discord.Permissions) -> bool:
    # Check if user has required privileges.
    perms2check = user.guild_permissions if user is not None else inter.app_permissions
    if (perms2check | perms) != perms2check:
        permstr = 'user' if user is not None else 'application'

        # Output fancy error embed.
        await cmderrembed(
            app,
            inter = inter,
            cmd   = cmd,
            type  = KiyokoAppCommandError.UINSUFFPERMS if user is not None else KiyokoAppCommandError.AINSUFFPERMS,
            desc  = f'This command requires higher {permstr} permissions.'
        )

        return False

    # Everything is fine; user has required privs.
    return True



# command group representing the /config command
class KiyokoCommandGroup_Config(discord.app_commands.Group):
    def __init__(self, app, name: str, desc: str):
        super().__init__(name = name, description = desc)

        self._app = app


    # Configures the 'mwidget' item, a little feature that displays the current
    # total member count as an inaccessible voice channel that is periodically
    # updated.
    #
    # Returns nothing.
    @discord.app_commands.command(name = 'mcwidget', description = 'configures the member count widget')
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(
        enabled = 'whether or not the widget should be actively updated',
        fmt     = 'custom format for the member widget; use \'{}\' as a placeholder for the member count'
    )
    async def cmd_mcwidget(self, inter: discord.Interaction, enabled: Optional[bool], fmt: Optional[str]) -> None:
        # Check if user has required privileges.
        if not await helper_hasperms(self._app, 'config mcwidget', inter, inter.user, discord.Permissions(administrator = True)):
            return
        # Check if the bot has the required permissions (i.e. 'manage channels').
        elif not await helper_hasperms(self._app, 'config mcwidget', inter, None, discord.Permissions(manage_channels = True)):
            return

        # Check if the 'fmt' argument contains a {} placeholder if it is to be overwritten.
        if fmt is not None:
            if fmt.find('{}') == -1:
                await cmderrembed(
                    self._app,
                    inter = inter,
                    cmd   = 'config mcwidget',
                    type  = KiyokoAppCommandError.INVPARAM,
                    desc  = 'Parameter ``fmt`` must contain a ``{}`` placeholder.'
                )

                return

        # If the entry does not exist in the guild config object, create it.
        gcfg = self._app.gcman.getgconfig(inter.guild_id)
        if gcfg.mwidget is None:
            gcfg.mwidget = (False, 0, 0, 0, 'Member Count: {}')

        # Update the state of the Member Count Widget.
        olden  = gcfg.mwidget[0]
        oldfmt = gcfg.mwidget[4]
        gcfg.mwidget = (
            gcfg.mwidget[0] if enabled is None else enabled,
            gcfg.mwidget[1],
            gcfg.mwidget[2],
            gcfg.mwidget[3],
            gcfg.mwidget[4] if fmt is None else fmt
        )
        # Update configuration in database.
        await kiyo_guild.updgsettings(self._app, gcfg)

        # Send response.
        await cfgupdembed(
            self._app,
            inter = inter,
            desc  = 'mcwidget',
            upd   = [
                ('enabled', olden, gcfg.mwidget[0]) if enabled is not None and olden != gcfg.mwidget[0] else None,
                ('fmt', oldfmt, gcfg.mwidget[4]) if fmt is not None and oldfmt != gcfg.mwidget[4] else None
            ]
        )
        logger.info(f'Updated \'mcwidget\' setting for guild with id: {gcfg.gid}: {gcfg.mwidget}')

    
    # Configures the 'logchan' item which controls the channel that logging messages
    # of the application will be sent to. The application needs to be able to send messages
    # in this channel.
    #
    # Returns nothing.
    @discord.app_commands.command(name = 'logchan', description = 'configures the logging channel the application will use')
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(
        enabled = 'whether or not logging to the logging channel is enabled',
        channel = 'channel to use for logging; preferably a private, staff-only channel'
    )
    async def cmd_logchan(self, inter: discord.Interaction, enabled: Optional[bool], channel: Optional[discord.TextChannel]) -> None:
        # Check if the command invoker has administrator permissions.
        if not await helper_hasperms(self._app, 'config logchan', inter, inter.user, discord.Permissions(administrator = True)):
            return
        
        # If the given channel is not None, check if the bot has the permission to send messages there.
        if channel is not None:
            if not channel.permissions_for(inter.guild.get_member(inter.client.user.id)).send_messages:
                await cmderrembed(
                    self._app,
                    inter = inter,
                    cmd   = 'config logchan',
                    type  = KiyokoAppCommandError.AINSUFFPERMS,
                    desc  = f'Application requires ``Send Messages`` permissions in channel <#{channel.id}>'
                )

                return

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

        # Send response.
        await cfgupdembed(
            self._app,
            inter = inter,
            desc  = 'logchan',
            upd   = [
                ('enabled', olden,   gcfg.logchan[0]) if enabled is not None and olden   != gcfg.logchan[0] else None,
                ('channel', oldchan, gcfg.logchan[1]) if channel is not None and oldchan != gcfg.logchan[1] else None
            ]
        )
        logger.info(f'Updated \'logchan\' setting for guild with id: {gcfg.gid}: {gcfg.logchan}')



# class representing the 'admin' module
class KiyokoModule_Admin(kiyo_mod.KiyokoModule_Base):
    # This command syncs the command tree (either guild-specific or global) to Discord.
    # Use it whenever a command has been added/removed. Note that this command can only
    # be used by the bot's owner.
    #
    # Returns nothing.
    @discord.app_commands.command(
        name        = 'sync',
        description = 'synchronizes commands to discord, requires application owner permissions'
    )
    @discord.app_commands.describe(private = 'only synchronize commands for the current guild; only for debugging')
    async def cmd_sync(self, inter: discord.Interaction, private: Optional[bool]) -> None:
        ispriv = False if private is None or private == False else True

        # Check if user has the owner of the application.
        if inter.user.id != inter.client.application.owner.id:
            await cmderrembed(
                self._app,
                inter = inter,
                cmd   = 'sync',
                type  = KiyokoAppCommandError.UINSUFFPERMS,
                desc  = 'Application command invoker must be the owner of the application.'
            )

            return

        # Check if command was run in a guild context if commands should only be synched
        # to the current guild.
        if inter.guild is None and ispriv == True:
            await cmderrembed(
                self._app,
                inter = inter,
                cmd   = 'sync',
                type  = KiyokoAppCommandError.INVEXECCTX,
                desc  = 'Command ``sync`` can only be run from a guild if ``private`` is ``True``.'
            )

            return

        # Sync commands locally or globally, depending on 'ispriv'.
        appendix = f'locally to guild \'{inter.guild.name}\' (id: {inter.guild_id})' if ispriv else 'globally'
        if ispriv:
            self._app.tree.copy_global_to(guild = inter.guild)
        else:
            await self._app.tree.sync()

        # Return response.
        response = fmtembed(
            color  = 0x6495ED,
            title  = 'Command Tree Synchronization',
            desc   = 'Successfully synchronized the command tree. Note that it may take up to one your before'
                    ' the new commands become available.',
            fields = [('Type', 'local' if ispriv == True else 'global', True)],
            footer = (f'Issued by {inter.user.display_name}', inter.user.display_avatar),
            thumb  = 'https://icons.iconarchive.com/icons/paomedia/small-n-flat/256/sign-sync-icon.png'
        )
        # When synching globally, it may happen that the response takes a long time which may be
        # enough to invalidate the interaction, throwing an exception.
        # In this case, we just catch the exception and return.
        try:
            await inter.response.send_message(embed = response)
        except:
            pass

        # Print message to log.
        logger.info(f'Synchronized commands {appendix}.')



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
    await app.add_cog(KiyokoModule_Admin(app))


