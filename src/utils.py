################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# utils.py - various utility functions needed in the entire application

# imports
import discord, datetime, time

from loguru import logger
from typing import Optional

import discord.ext.commands as commands

import src.error as kiyo_error



# Sends a message securely, that is, without throwing a 404 if the app took too long to respond.
#
# Returns nothing.
async def sendmsgsecure(inter, **kwargs) -> None:
    try:
        await (inter.response.send_message(**kwargs) if isinstance(inter, discord.Interaction) else inter.channel.send(**kwargs))
    except Exception as tmp_e:
        logger.error(
                 f'Could not send message in PM channel. Reason: {tmp_e}' if inter.guild is None
            else f'Could not send message (g: {inter.guild.id}, c: {inter.channel.id}). Reason: {tmp_e}'
        )



# General purpose function for formatting an embed in a more pretty and compact fashion.
#
# Returns prepared embed object.
def fmtembed(
    *,
    color:  int,
    title:  str,
    desc:   str,
    fields: Optional[list[tuple[str, any, bool]]] = None,
    footer: Optional[tuple[str, any]] = None,
    thumb:  Optional[str] = None,
    url:    Optional[str] = None,
    tstamp: Optional[datetime.datetime] = None
) -> discord.Embed:
    # Prepare embed object.
    res = discord.Embed(
        color       = color,
        title       = title,
        timestamp   = tstamp or datetime.datetime.now(),
        description = desc,
        url         = url
    )
    if footer is not None:
        (text, url) = footer

        res.set_footer(text = text, icon_url = url)
    if thumb is not None:
        res.set_thumbnail(url = thumb)

    # Add fields.
    if fields is not None:
        for field in fields:
            if field is None:
                continue
            (name, val, inl) = field

            res.add_field(name = name, value = val, inline = inl)

    # Finally, return object.
    return res


# Formats a standard embed shared by all devtool commands.
#
# Returns prepared embed and thumbnail file pointer.
def fmtdtoolembed(app, title: str, desc: str, fields: Optional[list[tuple[str, any, bool]]] = None) -> tuple[discord.Embed, discord.File]:
    file = discord.File(app.resman.getresource('devtools').url, filename = 'devtools.png')
    return (fmtembed(
        color  = 0x34495E,
        title  = title,
        desc   = desc,
        tstamp = datetime.datetime.now(),
        thumb  = 'attachment://devtools.png',
        fields = fields
    ), file)


# Call this function to send a generic embed in response of a '/config' command
# execution.
#
# Returns embed and thumbnail file.
def cfgupdembed(*, inter: discord.Interaction, desc: str, upd: list[tuple[str, any, any]], extra: str = None) -> tuple[discord.Embed, discord.File]:
    # Get thumbnail from local file.
    file = discord.File(inter.client.resman.getresource('settings').url, filename = 'settings.png')

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
        appendix = extra or '\n\n**Nothing to update!**'

    # Prepare and send embed.
    return (fmtembed(
        color  = 0x95a5a6,
        title  = 'Guild Configuration Update',
        desc   = f'Updated guild settings for ``{desc}``. Please note that some settings may take some time'
                  ' (i.e. until the next update of the module that uses the setting) until the changes take effect.' + appendix,
        fields = None,
        footer = (f'Issued by {inter.user.display_name}', inter.user.display_avatar),
        thumb  = 'attachment://settings.png'
    ), file)


# Helper function to format a guild configuration view embed.
#
# Returns embed and used thumbnail file.
def fmtcfgviewembed(*, inter: discord.Interaction, desc: str) -> tuple[discord.Embed, discord.File]:
    file = discord.File(inter.client.resman.getresource('settings').url, filename = 'settings.png')
    return (fmtembed(
        color  = 0x95a5a6,
        title  = 'Guild Configuration',
        desc   = desc,
        fields = None,
        footer = (f'Issued by {inter.user.display_name}', inter.user.display_avatar),
        thumb  = 'attachment://settings.png'
    ), file)


# Counts the number of top level commands the application supports.
#
# Returns number of application commands currently registered in the
# internal command tree.
def nappcmds(app) -> int:
     return sum(1 for x in app.tree.walk_commands() if isinstance(x, discord.app_commands.Command))


# Returns a set of all registered message and application commands.
# This includes both group (parent) commands and normal commands.
#
# Returns set holding all currently registered command instances.
def allcommands(app) -> set:
    # TODO: Expand child commands for prefix.
    return set([x for x in app.tree.walk_commands()] + [x for x in app.commands])


# Generates a list of strings from a comma-separated string.
#
# Returns list of strings.
def listfromstr(src: str, sep: str) -> list[str]:
    return src.strip().replace(' ', '').split(sep)


# Retrieves the total parameter count (including required and optional) parameters
# for a given application or prefix (message) command.
#
# Returns count.
def numcmdargs(cmd) -> int:
    return len(cmd.parameters) if hasattr(cmd, 'parameters') else 0



# Checks whether the application has the required permissions in the given channel.
#
# Returns True if the permission requirements are met, False if not.
def haschanperms(inter: discord.Interaction, chan: discord.abc.GuildChannel, perms: discord.Permissions) -> bool:
    # Get app permissions for the given channel.
    appperms = chan.permissions_for(inter.guild.get_member(inter.client.user.id))

    # Check whether the app satisfies all required channel permissions.
    return perms & appperms == perms


# Checks whether a command has a certain check.
#
# Returns True if the command depends on the given check,
# False if not.
def hascheck(cmd, check) -> bool:
    return hasattr(cmd, 'checks') and check.__qualname__ in [check.__qualname__ for check in cmd.checks]



# Checks whether the command invoker is actually a registered developer or the app
# owner.
#
# Returns True if yes, if not raises an MsgCmd_NotADeveloper exception.
async def isadev(ctx) -> bool:
    uid = ctx.author if isinstance(ctx, commands.Context) else ctx.user
    app = ctx.bot if isinstance(ctx, commands.Context) else ctx.client
    
    # If the user is not a registered developer and not the owner of the application,
    # raise the exception describing the error.
    if not uid in listfromstr(app.cfg.getvalue('upd', 'devids', ''), ',') and not await app.is_owner(uid):
        raise kiyo_error.MsgCmd_NotADeveloper

    # Nothing failed, so the user is a registered developer OR the owner
    # of the app, which implies developership.
    return True


# A simple check that allows us to verify that a command is invoked 
# from a PM. This is a requirement for all developer commands.
#
# Returns True if the context is PM, otherwise it raises a MsgCmd_OnlyPMChannel
# exception.
def ispmcontext(ctx) -> bool:
    if ctx.guild is not None:
        raise kiyo_error.MsgCmd_OnlyPMChannel

    return True


# A simple check verifying that the command invoker is the owner
# of the application.
#
# Returns True if the command invoker is the owner of the app,
# raises MissingPermissions if not.
async def isappowner(ctx) -> bool:
    uid = ctx.author if isinstance(ctx, commands.Context) else ctx.user
    app = ctx.bot if isinstance(ctx, commands.Context) else ctx.client

    # Raise the exception if the invoker is not the owner.
    if await app.is_owner(uid):
        raise discord.app_commands.MissingPermissions('')

    return True


# A simple check that verifies that the command we are using is
# globally enabled. If the command info could not be retrieved,
# we assume the command is enabled.
#
# Returns True if the command is enabled, or raises an exception if it
# is not.
def isenabled(ctx) -> bool:
    cmd = ctx.command
    app = ctx.bot if isinstance(ctx, commands.Context) else ctx.client
    
    info = app.cmdman.getcommandinfo(cmd.qualified_name)
    if info is not None and not info.enabled:
        raise kiyo_error.MsgCmd_CommandDisabled

    return True



# Let's abuse a check to update the command info cache before we invoke
# the command. Hence, this check cannot fail.
#
# Returns True.
def updcmdstats(ctx) -> bool:
    cmd = ctx.command
    app = ctx.bot if isinstance(ctx, commands.Context) else ctx.client

    info = app.cmdman.getcommandinfo(cmd.qualified_name)
    app.cmdman.updcommandinfo(cmd.qualified_name, count = info.count + 1, lastuse = int(time.time()))

    return True


