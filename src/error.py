################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# error.py - error codes used by this application

# imports
import discord

from loguru               import logger
from discord.app_commands import *
from discord.ext.commands import *

import src.utils as kiyo_utils



# This exception is thrown whenever an appliation command parameter is invalid.
class AppCmd_InvalidParameter(CheckFailure):
    pass

# This exception is thrown whenever the application is missing channel
# permissions.
class AppCmd_MissingChannelPermissions(CheckFailure):
    pass

# This exception is thrown whenever a command is owner-only but not invoked
# by the app owner.
class AppCmd_NotApplicationOwner(CheckFailure):
    pass

# This exception is thrown whenever sometimes implements a slot mechanic and all
# slots are currently occupied.
class AppCmd_AllSlotsOccupied(CheckFailure):
    pass


# Exception that is raised whenever a message command that is only supposed to
# be run from a PM channel is invoked in a guild context.
class MsgCmd_OnlyPMChannel(CommandError):
    pass

# This exception is thrown whenever a message command is developer-only but
# not invoked by a developer.
class MsgCmd_NotADeveloper(CommandError):
    pass

# This exception is thrown whenever a message command parameter represents
# a user (ID) and this user is not registered as a dev.
class MsgCmd_NoDev(CommandError):
    pass

# This exception is thrown whenever a message command parameter represents
# a user (ID) and this user does not exist globally.
class MsgCmd_NoSuchUser(CommandError):
    pass

# This exception is thrown whenever a message command parameter represents
# a user (ID) and this user is already registered as a dev.
class MsgCmd_AlreadyDev(CommandError):
    pass

# This exception is thrown whenever a sub-command for an invoked command
# group could not be found.
class MsgCmd_InvalidSubCommand(CommandError):
    pass



# Error code dictionary, mapping error codes to a string that will
# be displayed to the user.
gl_errordesc: dict[type, str] = {
    # application command errors
    NoPrivateMessage:                 'This command can only be executed in a guild context.',
    MissingRole:                      'You lack a role to execute this command.',
    MissingPermissions:               'You require higher permissions in order to execute this command.',
    BotMissingPermissions:            'The application does not have the required permissions.',
    CommandOnCooldown:                'The command is on cooldown.',
    AppCmd_InvalidParameter:          'A command parameter is invalid.',
    AppCmd_MissingChannelPermissions: 'The application is missing channel permissions.',
    AppCmd_NotApplicationOwner:       'This command can only be invoked by the owner of this application.',
    AppCmd_AllSlotsOccupied:          'All slots are currently occupied.',

    # message command errors
    CommandInvokeError:               'Could not successfully complete command callback. This is likely a bug in the callback\'s code '
                                      'and should be fixed by the maintainer of this application.',
    NotOwner:                         'This command can only be invoked by the owner of the application.',
    BadArgument:                      'Could not convert message command parameter.',
    MissingRequiredArgument:          'The command invokation context is missing a required parameter.',
    MsgCmd_NotADeveloper:             'This command can only be invoked by the owner of this application or a registered developer.',
    MsgCmd_OnlyPMChannel:             'This message command can only be invoked from a PM channel.',
    MsgCmd_NoDev:                     'The user with the given ID is not registered as a developer.',
    MsgCmd_NoSuchUser:                'A user with the given ID does not exist.',
    MsgCmd_AlreadyDev:                'The user with the given ID is already registered as a developer.',
    MsgCmd_InvalidSubCommand:         'Tried to invoke a sub-command that does not exist.'
}


# Call this function in case of an application command error.
# Sends a fancy embed describing the error in detail.
# 
# Returns the prepared error embed, also returns the file object
# pointing to the thumbnail so it can be sent via the interaction.
def cmderrembed(
    app,
    *,
    inter: discord.Interaction | Context,
    err: discord.app_commands.AppCommandError | CommandError
) -> tuple[discord.Embed, discord.File]:
    # Get thumbnail from local file.
    file = discord.File(app.resman.getresource('error').url, filename = 'error.png')

    # Get error message.
    errmsg = gl_errordesc.get(type(err)) or ''

    # Get full command name, taking into account if the command is a sub-command
    # (i.e. part of a group). Note that this does not account for nested groups
    # for it is not needed right now. This code will be extended to support arbitrary
    # nesting levels once the first command utilizing it is introduced.
    fname = inter.command.name
    if inter.command.parent:
        fname = inter.command.parent.name + ' ' + fname

    # Generate fancy explanatory embed.
    return (kiyo_utils.fmtembed(
        color  = 0xFF3030,
        title  = f'{"Application" if isinstance(inter, discord.Interaction) else "Message"} Command Error',
        desc   = f'While processing command ``{fname}``, an error occurred! Please use '
                 f'``{app.cfg.getvalue("global", "prefix", "/")}help {fname}`` for detailed usage of this command.',
        fields = [('Description', errmsg or f'Unknown error ({type(err).__name__}).', False)],
        thumb  = 'attachment://error.png'
    ), file)



# subclass of CommandTree in order to override the 'on_error' event
# handler
class KiyokoCommandTree(discord.app_commands.CommandTree):
    # Overrides the 'on_error' event handler so that we can process errors
    # application command errors globally.
    #
    # Returns nothing.
    async def on_error(self, inter: discord.Interaction, err: discord.app_commands.AppCommandError) -> None:
        # Prepare embed.
        (embed, file) = cmderrembed(self.client, inter = inter, err = err)

        # Send message.
        guildstr = inter.guild.name if inter.guild is not None else 'none'
        logger.error(
            f'Exception in command \'{inter.command.name}\' (guild: \'{guildstr}\'). '
            f'Desc: {gl_errordesc.get(type(err)) or type(err).__name__}'    
        )
        await kiyo_utils.sendmsgsecure(inter, file = file, embed = embed, ephemeral = True)


