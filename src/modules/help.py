################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# help.py - interactive help command, utilizing GUI

# imports
import discord, discord.ui, discord.enums

from typing import *
from loguru import logger

import discord.ext.commands as commands

import src.module as kiyo_mod
import src.utils  as kiyo_utils
import src.error  as kiyo_error



# class holding the '/help' command
class KiyokoModule_Help(kiyo_mod.KiyokoModule_Base):
    # commands per page in 'overview' mode
    CMDSPERPAGE = 8

    # enumeration describing command types
    class KiyokoCommandType:
        def __init__(self, **kwargs):
            self.appcmd   = kwargs.get('appcmd', False)
            self.subcmd   = kwargs.get('subcmd', False)
            self.group    = kwargs.get('group', False)
            self.msgcmd   = kwargs.get('msgcmd', False)
            self.devcmd   = kwargs.get('devcmd', False)
            self.ownercmd = kwargs.get('ownercmd', False)
            self.guildcmd = kwargs.get('guildcmd', False)
            self.pmcmd    = kwargs.get('pmcmd', False)


    # Generates a list of commands the user with given permissions can view.
    # Takes into account guild permissions, dev status, owner status, etc.
    #
    # Returns list of qualified command names.
    async def __enumeratecmdsforuser(self, inter: discord.Interaction) -> list[dict[str, any]]:
        # Generates an object, describing a command's properties in detail.
        #
        # Returns object.
        def __createcmdflags(cmd) -> self.KiyokoCommandType:
            return self.KiyokoCommandType(
                appcmd   = hasattr(cmd, 'default_permissions'),
                issubcmd = cmd.parent is not None,
                group    = hasattr(cmd, 'commands'),
                devcmd   = kiyo_utils.hascheck(cmd, kiyo_utils.isadev),
                pmcmd    = kiyo_utils.hascheck(cmd, kiyo_utils.ispmcontext),
                guildcmd = hasattr(cmd, 'guild_only') and cmd.guild_only,
                ownercmd = kiyo_utils.hascheck(cmd, kiyo_utils.isappowner)
            )

        # Create result list.
        res     = []
        # Create a list of all commands that are currently registered.
        allcmds = [(x, __createcmdflags(x)) for x in kiyo_utils.allcommands(self._app)]
        # Get user's permissions.
        perms   = inter.guild.get_member(inter.user.id).guild_permissions if inter.guild is not None else None

        # Add all application commands that the user has enough guild permissions for.
        res += [cmd for (cmd, flags) in allcmds if flags.appcmd]
        # Add all developer commands if the invoker is a developer. Note that the
        # application owner is also by definition a developer.
        if await kiyo_utils.isadev(inter):
            res += [cmd for (cmd, flags) in allcmds if flags.devcmd]
        # Add owner-only commands if the invoker is the application owner.
        if await self._app.is_owner(inter.user):
            res += [cmd for (cmd, flags) in allcmds if flags.ownercmd]

        # Return resulting command name list.
        return res


    # Sorts a list of commands by a given criterion. The original list is not modified.
    #
    # Returns sorted list.
    def sortbycriterion(self, input: list, crit: int) -> list:
        # Get command info for each command.
        infolist = [(x, self._app.cmdman.getcommandinfo(x)) for x in input]
        
        # Sort list.
        match crit:
            case 1:
                # Variant 1: Sort alphabetically.
                infolist.sort(key = lambda _, info: info.cmdname)
            case 2:
                # Variant 2: Sort by significance. reverse = True because
                # we want to see most-used commands first.
                infolist.sort(key = lambda _, info: info.count, reverse = True)
            case 3:
                # Variant 3: Sort by parameter count.
                infolist.sort(key = lambda cmd, _: kiyo_utils.numcmdargs(cmd))
            case 4:
                # Variant 4: Sort by time of existence. reverse = True because
                # we want to see newest commands first.
                infolist.sort(key = lambda _, info: info.added, reverse = True)

        # Return only the commands.
        return [x for (x, _) in infolist]



    # Auto-complete for the 'filters' argument, will show only the filters
    # the user is allowed to use.
    #
    # Returns a list of strings the user can enter for filters.
    async def cmdhelp_filters_autocompl(self, inter: discord.Interaction, current: str) -> List[discord.app_commands.Choice[str]]:
        # Compile the filters the user can use.
        filters = ['guild-only commands', 'PM-only commands', 'only sub-commands', 'only parent-commands']
        if await kiyo_utils.isadev(inter):
            filters += 'developer-only commands'
        if await kiyo_utils.isappowner(inter):
            filters += 'owner-only commands'

        # Generate list of valid choices.
        return [discord.app_commands.Choice(name = x, value = x) for x in filters]


    # Auto-complete for the 'commands' argument, will show only the commands
    # the user is allowed to use.
    #
    # Returns a list of command name strings the user can enter for the 
    # 'commands' parameter.
    async def cmdhelp_commands_autocompl(self, inter: discord.Interaction, current: str) -> List[discord.app_commands.Choice[str]]:
        # Generate list of choices.
        return [
            discord.app_commands.Choice(name = cmd['cmd'].qualified_name, value = cmd['cmd'].qualified_name)
            for cmd in await self.__enumeratecmdsforuser(inter)
        ]


    # Implements an interactive help command, featuring advanced filter options, in-depth
    # explanations and controls via GUI.
    #
    # Returns nothing.
    @discord.app_commands.command(
        name        = 'help',
        description = 'interactive help providing in-depth guidance on each command, supports filtering'
    )
    @discord.app_commands.describe(
        commands = 'name(s) of the specific command(s) to show the help page of - comma-separated; default: show all',
        filters  = 'filters(s) to apply to the command listing - comma-separated; default: none',
        overview = 'whether to show a brief overview or a detailed page for every command; default: True',
        orderby  = 'order results by a predefined criterion; default: Alphabet'
    )
    @discord.app_commands.choices(
        orderby = [
            discord.app_commands.Choice(name = 'alphabet (ASC)',        value = 1),
            discord.app_commands.Choice(name = 'significance (DESC)',   value = 2),
            discord.app_commands.Choice(name = 'parameter count (ASC)', value = 3),
            discord.app_commands.Choice(name = 'newest (DESC)',         value = 4)
        ]
    )
    @discord.app_commands.autocomplete(commands = cmdhelp_commands_autocompl, filters = cmdhelp_filters_autocompl)
    @discord.app_commands.check(kiyo_utils.isenabled)
    @discord.app_commands.check(kiyo_utils.updcmdstats)
    async def cmd_help(
        self,
        inter: discord.Interaction,
        overview: Optional[bool] = True,
        commands: Optional[str] = 'all',
        filters: Optional[str] = '',
        orderby: Optional[discord.app_commands.Choice[int]] = 1
    ) -> None:
        raise kiyo_error.AppCmd_NotImplemented
        # Get a list of all command that the user can use, taking into account guild permissions,
        # developer status, and owner status.
        #reslist = await self.__enumeratecmdsforuser(inter)
        # Sort command list using the given criterion.
        #reslist = self.sortbycriterion([x for x, _ in reslist], orderby)

         

# module entrypoint
async def setup(app) -> None:
    await app.add_cog(KiyokoModule_Help(app))


