################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# error.py - error codes used by this application

# imports
import discord
import json

import jsonschema
import jsonschema.exceptions
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

# This exception is thrown whenever an application command is executed that does
# not exist (any longer).
class AppCmd_NotFound(CheckFailure):
    pass

# This exception is thrown whenever an application command is added to the tree
# but is still not implemented.
class AppCmd_NotImplemented(CheckFailure):
    pass

# This exception is thrown when the module configuration is not complete.
class AppCmd_IncompleteConfig(CheckFailure):
    pass

# This exception is thrown when ther caller does not have sufficient permissions to invoke
# the command.
class AppCmd_MissingPermissions(CheckFailure):
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

# This exception is thrown whenever a command depends on a misconfigured
# setting.
class MsgCmd_InvalidConfiguration(CommandError):
    pass

# This exception is thrown whenever a command is being invoked that is currently
# globally disabled.
class MsgCmd_CommandDisabled(discord.app_commands.AppCommandError):
    pass




# Error code dictionary, mapping error codes to a string that will
# be displayed to the user.
gl_errordesc: dict[type, str] = {
    # raw exceptions
    discord.HTTPException:                 'Could not download the attachment.',
    discord.Forbidden:                     'You do not have permissions to access this attachment.',
    discord.NotFound:                      'The attachment was deleted.',
    json.JSONDecodeError:                  'Could not decode the JSON document. It is likely malformed.',
    jsonschema.exceptions.SchemaError:     'Could not load JSON schema for validation: Schema is likely malformed or could not be found.',
    jsonschema.exceptions.ValidationError: 'Could not validate JSON against schema. JSON document is likely malformed.',

    # application command errors
    NoPrivateMessage:                      'This command can only be executed in a guild context.',
    MissingRole:                           'You lack a role to execute this command.',
    MissingPermissions:                    'You require higher permissions in order to execute this command.',
    BotMissingPermissions:                 'The application does not have the required permissions.',
    CommandOnCooldown:                     'The command is on cooldown.',
    CommandSignatureMismatch:              'Command signatures are incongruent; this is likely because '
                                           'of a command update without a sync. Contact the owner of the application.',
    AppCmd_InvalidParameter:               'A command parameter is invalid.',
    AppCmd_MissingChannelPermissions:      'The application is missing channel permissions.',
    AppCmd_NotApplicationOwner:            'This command can only be invoked by the owner of this application.',
    AppCmd_AllSlotsOccupied:               'All slots are currently occupied.',
    AppCmd_NotFound:                       'This application command could not be found. It\'s likely it got removed. '
                                           'Please contact the owner of the application.',
    AppCmd_NotImplemented:                 'This command has yet to be implemented.',
    AppCmd_IncompleteConfig:               'The parent module\'s configuration for this command is incomplete.',
    AppCmd_MissingPermissions:             'You require higher permissions in order to execute this command.',

    # message command errors
    CommandInvokeError:                    'Could not successfully complete command callback. This is likely a bug in the callback\'s code '
                                           'and should be fixed by the maintainer of this application.',
    NotOwner:                              'This command can only be invoked by the owner of the application.',
    BadArgument:                           'Could not convert message command parameter.',
    MissingRequiredArgument:               'The command invokation context is missing a required parameter.',
    MsgCmd_NotADeveloper:                  'This command can only be invoked by the owner of this application or a registered developer.',
    MsgCmd_OnlyPMChannel:                  'This message command can only be invoked from a PM channel.',
    MsgCmd_NoDev:                          'The user with the given ID is not registered as a developer.',
    MsgCmd_NoSuchUser:                     'A user with the given ID does not exist.',
    MsgCmd_AlreadyDev:                     'The user with the given ID is already registered as a developer.',
    MsgCmd_InvalidSubCommand:              'Tried to invoke a sub-command that does not exist.',
    MsgCmd_InvalidConfiguration:           'Could not invoke command due to invalid configuration.',
    MsgCmd_CommandDisabled:                'The command or sub-command that was being invoked is globally disabled.'
}


# Call this function in case of an application command error.
# Sends a fancy embed describing the error in detail.
# 
# Returns the prepared error embed, also returns the file object
# pointing to the thumbnail so it can be sent via the interaction.
def cmderrembed(
    app,
    *,
    inter,
    err
) -> tuple[discord.Embed, discord.File]:
    # Get thumbnail from local file.
    file = discord.File(app.resman.getresource('error').url, filename = 'error.png')

    # Get error message.
    cmd    = inter.command
    errmsg = gl_errordesc.get(type(err)) or ''

    # Get full command name, taking into account if the command is
    # a sub-command (i.e. part of a group). Takes into account
    # arbitrarily nested sub-commands.
    fname = cmd.qualified_name

    # Generate fancy explanatory embed.
    return (kiyo_utils.fmtembed(
        color  = 0xE74C3C,
        title  = f'Command Error',
        desc   = f'While invoking command ``{fname}``, an error occurred. Please use '
                 f'</help:1144501967494844460> with ``commands:{fname}`` for detailed usage of this command. '
                  'Also refer to the error message given below (see ``Description``).',
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
        # If the command simply could not be found, present a message describing the error.
        if inter.command is None:
            logger.error(
                'Tried to invoke an application command that does not exist. That\'s likely because '
                'the command existed, got removed but no \'/sync\' was run to remove the command '
                'signature from the global command tree.'
            )
        else:
            typename = type(err.original if hasattr(err, '') else err).__name__
            typedesc = gl_errordesc.get(type(err.original if hasattr(err, 'original') else err))
            guildstr = inter.guild.name if inter.guild is not None else 'none'
            logger.error(
                f'Exception in command \'{inter.data.get("name")}\' (guild: \'{guildstr}\'). '
                f'Desc: {typedesc or typename}'    
            )

        # Prepare embed.
        exctype       = err.original if hasattr(err, 'original') else err
        (embed, file) = cmderrembed(self.client, inter = inter, err = AppCmd_NotFound() if inter.command is None else exctype)
        # Send descriptive error message.
        await kiyo_utils.sendmsgsecure(inter, file = file, embed = embed, ephemeral = True)


