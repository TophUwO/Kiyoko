################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# utils.py - various utility functions needed in the entire application

# imports
import discord, datetime

from loguru import logger
from typing import Optional

import discord.ext.commands as commands

import src.error as kiyo_error



# Sends a message securely, that is, without throwing a 404 if the app took too long to respond.
#
# Returns nothing.
async def sendmsgsecure(inter: discord.Interaction | commands.Context, **kwargs) -> None:
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
def cfgupdembed(app, *, inter: discord.Interaction, desc: str, upd: list[tuple[str, any, any]], extra: str = None) -> tuple[discord.Embed, discord.File]:
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
        appendix = extra or '\n\n**Nothing to update!**'

    # Prepare and send embed.
    return (fmtembed(
        color  = 0x28AEFF,
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
def fmtcfgviewembed(app, *, inter: discord.Interaction, desc: str) -> tuple[discord.Embed, discord.File]:
    file = discord.File(app.resman.getresource('settings').url, filename = 'settings.png')
    return (fmtembed(
        color  = 0x28AEFF,
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
     return sum(1 for x in app.tree.walk_commands() if type(x) == discord.app_commands.Command)



# Checks whether the application has the required permissions in the given channel.
#
# Returns True if the permission requirements are met, False if not.
def haschanperms(inter: discord.Interaction, chan: discord.abc.GuildChannel, perms: discord.Permissions) -> bool:
    # Get app permissions for the given channel.
    appperms = chan.permissions_for(inter.guild.get_member(inter.user.id))

    # Check whether the app satisfies all required channel permissions.
    return appperms | perms == appperms


def msgcmd_ispm(ctx: commands.Context) -> bool:
    if ctx.guild is not None:
        raise kiyo_error.MsgCmd_OnlyPMChannel

    return True


