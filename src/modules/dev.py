################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# dev.py - integrated development and maintenance tools

# imports
import discord, time, datetime

from loguru               import logger
from typing               import Optional
from discord.app_commands import *

import discord.ext.commands as commands

import src.module as kiyo_mod
import src.error  as kiyo_error
import src.utils  as kiyo_utils
        


# commands for managing the application, doing maintenance
class KiyokoModule_Dev(kiyo_mod.KiyokoModule_Base):
    def __init__(self, app):
        super().__init__(app)

        # Initialize developer list. These are all clients that can execute
        # any of these commands. Because the application is self-hosted, there
        # are no registered developers by default. However, the owner of the
        # application is guaranteed to be able to run these commands in every
        # case.
        self._appowner = 0
        self._devids   = set()
        adddevids = self._app.cfg.getvalue('upd', 'devids', '').strip().replace(' ', '')
        if adddevids is not None and adddevids != '':
            try:
                self._devids = set(map(int, adddevids.split(',')))
            except Exception as tmp_e:
                logger.error(f'Failed to load registered developer IDs. Reason: {tmp_e}')


    # Adds a developer to the dev list. Automatically refreshes the disk file.
    # Nothing will be done if the user ID already exists in the list.
    #
    # Returns True if the user was added, False if not.
    def __adddev(self, id: int) -> bool:
        oldlen = len(self._devids)
        self._devids.add(id)

        return oldlen != len(self._devids)

    
    # Removes a developer from the dev list. Automatically refreshes the disk file.
    # If the user ID is not in the list, nothing will be done.
    #
    # Returns True if the user was removed, False if not.
    def __remdev(self, id: int) -> bool:
        try:
            self._devids.remove(id)

            return True
        except KeyError:
            return False


    # Returns a generator that lets us iterate through all user IDs.
    #
    # Returns developer IDs as long as there are some left unconsumed.
    def __devids(self) -> int:
        for id in self._devids:
            yield id


    # Parent command for '/env'. Handles developer management.
    #
    # Returns nothing.
    @commands.group(name = 'env', pass_context = True)
    @commands.check(kiyo_utils.isadev)
    @commands.check(kiyo_utils.ispmcontext)
    @commands.check(kiyo_utils.isenabled)
    @commands.check(kiyo_utils.updcmdstats)
    async def msgcmd_env(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            raise kiyo_error.MsgCmd_InvalidSubCommand


    # Shows the value of either a list of global settings or all global settings.
    # Global settings can only be viewed by the application owner and registered
    # developers.
    #
    # Returns nothing.
    @msgcmd_env.command(name = 'get')
    @commands.check(kiyo_utils.isadev)
    @commands.check(kiyo_utils.ispmcontext)
    @commands.check(kiyo_utils.isenabled)
    @commands.check(kiyo_utils.updcmdstats)
    async def cmd_get(self, ctx: commands.Context, settings: Optional[str]) -> None:
        # Get list of settings from input. This will filter out duplicate settings
        # by default. If 'settings' is not set or explicitly set to 'all', all settings
        # in the 'global' section will be retrieved. 
        errset = set(); clsset = set()
        if settings is None or settings == 'all':
            clsset = set([x for x in self._app.cfg.globalkeys()])
        else:
            setl   = set([] if settings is None else settings.strip().replace(' ', '').split(','))
            errset = set(set([x for x in setl if self._app.cfg.getvalue('global', x, None) is None]))
            clsset = set(setl - errset) 

        # Prepare embed text.
        longest = len(max(clsset, key = len))
        desc    = '```coffee' if len(clsset) > 0 else 'No existing global settings queried.'
        err     = ', '.join(errset)
        for opt in clsset:
            # Get value of global setting.
            val = self._app.cfg.getvalue('global', opt, None)

            # Format it nicely.
            pad  = (longest - len(opt)) * ' '
            desc += f'\n{opt}{pad} =-> {val}'
        desc += '\n```'

        # Prepare and send response.
        (embed, file) = kiyo_utils.fmtdtoolembed(
            app    = self._app,
            title  = 'Global Configuration',
            desc   = desc,
            fields = [
                ('Not found', err, False) if err != '' else None    
            ]
        )
        await kiyo_utils.sendmsgsecure(ctx, file = file, embed = embed)


    # Overwrites global settings. Can only be run by the app owner and registered developers.
    #
    # Returns nothing.
    @msgcmd_env.command(name = 'set')
    @commands.check(kiyo_utils.isadev)
    @commands.check(kiyo_utils.ispmcontext)
    @commands.check(kiyo_utils.isenabled)
    @commands.check(kiyo_utils.updcmdstats)
    async def cmd_set(self, ctx: commands.Context, option: str, value: str, flush: Optional[bool] = True) -> None:
        # Check if given settings key exists.
        option = option.strip()
        oldval = self._app.cfg.getvalue('global', option, None)
        if oldval is None:
            raise kiyo_error.InvalidParameter

        # Update global setting and flush disk file if requested.
        self._app.cfg.setvalue('global', option, value)
        if flush:
            self._app.cfg.writeconfig()

        # Prepare and send response.
        desc  = f'The following global setting has been updated:\n```coffee\n{option} =-> {oldval} => {value}\n```'
        (embed, file) = kiyo_utils.fmtdtoolembed(
            app    = self._app,
            title  = 'Global Configuration',
            desc   = desc,
            fields = [('Flushed?', 'yes' if flush else 'no', False)]
        )
        await kiyo_utils.sendmsgsecure(ctx, embed = embed, file = file)


    # Adds a new field to the [global] section of the global configuration file. Optionally,
    # the user can provide an initial value. This command can only be used by developers.
    #
    # Returns nothing.
    @msgcmd_env.command(name = 'add')
    @commands.check(kiyo_utils.isadev)
    @commands.check(kiyo_utils.ispmcontext)
    @commands.check(kiyo_utils.isenabled)
    @commands.check(kiyo_utils.updcmdstats)
    async def cmd_add(self, ctx: commands.Context, option: str, initval: Optional[str], flush: Optional[bool] = True) -> None:
        pass


    # Removes a field from the [global] section of the global configuration file. This command
    # can only be invoked by developers.
    #
    # Returns nothing.
    @msgcmd_env.command(name = 'del')
    @commands.check(kiyo_utils.isadev)
    @commands.check(kiyo_utils.ispmcontext)
    @commands.check(kiyo_utils.isenabled)
    @commands.check(kiyo_utils.updcmdstats)
    async def cmd_rem(self, ctx: commands.Context, option: str, flush: Optional[bool] = True) -> None:
        pass


    # Parent command for '/dev'. Handles developer management.
    #
    # Returns nothing.
    @commands.group(name = 'dev', pass_context = True)
    @commands.check(kiyo_utils.isappowner)
    @commands.check(kiyo_utils.ispmcontext)
    @commands.check(kiyo_utils.isenabled)
    @commands.check(kiyo_utils.updcmdstats)
    async def msgcmd_dev(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            raise kiyo_error.MsgCmd_InvalidSubCommand


    # Registers a developer. After this, the user with that ID will
    # be able to use all developer-only commands immediately. This command
    # can only be run by the owner of the application.
    #
    # Returns nothing.
    @msgcmd_dev.command(name = 'reg')
    @commands.check(kiyo_utils.isappowner)
    @commands.check(kiyo_utils.ispmcontext)
    @commands.check(kiyo_utils.isenabled)
    @commands.check(kiyo_utils.updcmdstats)
    async def msgcmd_reg(self, ctx: commands.Context, userid: str) -> None:
        userid = int(userid)

        # Check if the user with the given ID exists.
        try:
            await self._app.fetch_user(userid)
        except discord.NotFound:
            raise kiyo_error.MsgCmd_NoSuchUser

        # Add user to devid list.
        if self.__adddev(userid):
            # Refresh disk file.
            self._app.cfg.setvalue('upd', 'devids', ', '.join(map(str, self.__devids())))
            self._app.cfg.writeconfig()
            logger.info(f'Registered developer with ID {userid}.')

            # Prepare and send response.
            (embed, file) = kiyo_utils.fmtdtoolembed(
                app   = self._app,
                title = 'Developer Management',
                desc  = f'The developer with the ID ``{userid}`` was successfully registered.'
                         'They can now use all developer-only commands.'
            )
            await kiyo_utils.sendmsgsecure(ctx, embed = embed, file = file)
        else:
            # If the user is already registered, show an error message.
            raise kiyo_error.MsgCmd_AlreadyDev


    # Removes a developer from the list of registered developers. This command
    # can only be run by the owner of the application.
    #
    # Returns nothing.
    @msgcmd_dev.command(name = 'unreg')
    @commands.check(kiyo_utils.isappowner)
    @commands.check(kiyo_utils.ispmcontext)
    @commands.check(kiyo_utils.isenabled)
    @commands.check(kiyo_utils.updcmdstats)
    async def cmd_unreg(self, ctx: commands.Context, userid: str) -> None:
        userid = int(userid)

        if self.__remdev(userid):
            # Refresh disk file.
            self._app.cfg.setvalue('upd', 'devids', ', '.join(map(str, self.__devids())))
            self._app.cfg.writeconfig()
            logger.info(f'Unregistered developer with ID {userid}.')

            # Prepare and send response.
            (embed, file) = kiyo_utils.fmtdtoolembed(
                app   = self._app,
                title = 'Developer Management',
                desc  = f'The developer with the ID ``{userid}`` was successfully unregistered.'
                         'They can no longer use developer-only commands.'
            )
            await kiyo_utils.sendmsgsecure(ctx, embed = embed, file = file)
        else:
            # If the user is already registered, show an error message.
            raise kiyo_error.MsgCmd_NoDev


    # Shows a list of all registered developer user IDs.
    #
    # Returns nothing.
    @msgcmd_dev.command(name = 'list')
    @commands.check(kiyo_utils.isappowner)
    @commands.check(kiyo_utils.ispmcontext)
    @commands.check(kiyo_utils.isenabled)
    @commands.check(kiyo_utils.updcmdstats)
    async def cmd_list(self, ctx: commands.Context) -> None:
        # Prepare message description.
        i    = 1
        desc = ''
        for dev in self.__devids():
            # Fetch user.
            user = await self._app.fetch_user(dev)
 
            desc += f'\n{i}. {user.name}#{user.discriminator} (id: ``{dev}``)'
            i += 1
 
        # Prepare and send response.
        (embed, file) = kiyo_utils.fmtdtoolembed(
            app   = self._app,
            title = 'Developer Management',
            desc  = desc or 'No registered developers.'
        )
        await kiyo_utils.sendmsgsecure(ctx, embed = embed, file = file)


    # Shows application status, nicely formatted.
    #
    # Returns nothing.
    @commands.command(name = 'status')
    @commands.check(kiyo_utils.isadev)
    @commands.check(kiyo_utils.ispmcontext)
    @commands.check(kiyo_utils.isenabled)
    @commands.check(kiyo_utils.updcmdstats)
    async def msgcmd_status(self, ctx: commands.Context) -> None:
        # Query information to be displayed.
        appname   = self._app.cfg.getvalue('global', 'name', 'Kiyoko')
        nguilds   = len(self._app.guilds)
        upt       = str(datetime.timedelta(seconds = int(time.time()) - self._app.stime))
        ver       = self._app.cfg.getvalue('upd', 'version', 'unknown')
        rlimited  = 'yes' if self._app.is_ws_ratelimited() else 'no'
        ncommands = kiyo_utils.nappcmds(self._app)
        lsync     = time.strftime('%m/%d/%y %H:%M:%S', time.gmtime(int(self._app.cfg.getvalue('upd', 'lastsync', 0))))
        ndevs     = len(self._devids)

        # Prepare and send response.
        (embed, file) = kiyo_utils.fmtdtoolembed(
            app   = self._app,
            title = 'Application Status',
            desc  = 'Real-time application statistics.'
            '```coffee\n'
                f'name     =-> {appname}\n'
                f'version  =-> {ver}\n'
                f'guilds   =-> {nguilds}\n'
                f'uptime   =-> {upt}\n'
                f'rlimited =-> {rlimited}\n'
                f'commands =-> {ncommands}\n'
                f'lsync    =-> {lsync}\n'
                f'devs     =-> {ndevs}\n'
                f'ownerid  =-> {self._appowner}\n'
            '```'
        )
        await kiyo_utils.sendmsgsecure(ctx, file = file, embed = embed)


    # This command syncs the command tree to Discord. Use it whenever
    # a command has been added/removed. Note that this command can only
    # be used by the app's owner and registered developers. Synchronization
    # may take up to an hour.
    #
    # Returns nothing.
    @commands.command(name = 'sync')
    @commands.check(kiyo_utils.isadev)
    @commands.check(kiyo_utils.ispmcontext)
    @commands.check(kiyo_utils.isenabled)
    @commands.check(kiyo_utils.updcmdstats)
    async def msgcmd_sync(self, ctx: commands.Context, guild: Optional[discord.Guild | str]) -> None:
        # If 'guild' is a special key-word, get the developer guild of this application.
        if isinstance(guild, str) and guild.lower() in ['dev', 'debug', 'dbg', 'developer']:
            dgid = self._app.cfg.getvalue('global', 'devguild')
            if dgid is None or dgid == '':
                raise kiyo_error.MsgCmd_InvalidConfiguration

            guild = ctx.bot.get_guild(int(dgid))
        # Check whether to sync globally or locally.
        ispriv = guild is not None or False

        # Sync commands locally or globally, depending on 'ispriv'.
        appendix = f'locally to guild ``{guild.name}`` (id: ``{guild.id}``)' if ispriv else 'globally'
        if ispriv:
            self._app.tree.copy_global_to(guild = guild)
        else:
            await self._app.tree.sync()
        logger.info(f'Synchronized commands {appendix}.')

        # Update lastsync.
        self._app.cfg.setvalue('upd', 'lastsync', int(time.time()))
        self._app.cfg.writeconfig()

        # Send confirmation message.
        file = discord.File(self._app.resman.getresource('sync').url, filename = 'sync.png')
        embed = kiyo_utils.fmtembed(
            color  = 0x6495ED,
            title  = 'Command Tree Synchronization',
            desc   = f'Successfully synchronized the command tree {appendix}.' +
                      'Note that it may take up to one your before '
                      'the new commands become available.',
            fields = [
                ('Type', 'local' if ispriv == True else 'global', True),
                ('Count', f'{kiyo_utils.nappcmds(self._app)}', True)
            ],
            thumb  = 'attachment://sync.png'
        )
        await kiyo_utils.sendmsgsecure(ctx, embed = embed, file = file)


    # Global message command error handler; called whenever a message command (not an application
    # command) raises an exception or a check fails.
    #
    # Returns nothing.
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, err: commands.CommandError) -> None:
        # If the error is that the command can only be invoked from a PM, or if the invoker is not
        # a registered developer or the owner of the application, ignore the error (i.e. do not even
        # send an error message).
        if isinstance(err, kiyo_error.MsgCmd_OnlyPMChannel) or not await kiyo_utils.isadev(ctx):
            logger.error(
                f'Developer-only command invoked by non-developer \'{ctx.author.name}\' '
                f'(id: {ctx.author.id}) or invoked by a developer in a non-PM channel.'
            )

            return
        # If the command could not be found, simply ignore it for it could have been meant for a
        # different application, etc.
        elif ctx.command is None:
            return

        # Prepare embed.
        (embed, file) = kiyo_error.cmderrembed(self._app, inter = ctx, err = err)

        # Send error message.
        guildstr = ctx.guild.name if ctx.guild is not None else 'PM'
        logger.error(
            f'Exception in command \'{ctx.command.name}\' (guild: \'{guildstr}\'). '
            f'Desc: {kiyo_error.gl_errordesc.get(type(err)) or type(err).__name__}'    
        )
        await kiyo_utils.sendmsgsecure(ctx, file = file, embed = embed)
    


# module entrypoint
async def setup(app) -> None:
    # Register devtools.
    await app.add_cog(KiyokoModule_Dev(app))


