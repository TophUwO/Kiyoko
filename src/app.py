################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# app.py - main class, prepresenting application instance

# imports
import sys, os, traceback, configparser
import discord, time
import discord.ext.commands as commands
import urllib.request       as req
import distutils.version    as vcmp

from loguru import logger

import src.config        as kiyo_cfg
import src.db            as kiyo_db
import src.module        as kiyo_mod
import src.modules.guild as kiyo_mguild
import src.res           as kiyo_res
import src.error         as kiyo_error



# This class reimplements certain aspects of the event handlers, etc.
class KiyokoApplication(commands.Bot):
    def __init__(self) -> None:
        # Setup logging.
        self.__initlogging()

        # Load global config.
        self.cfg   = kiyo_cfg.KiyokoGlobalConfig('conf/.env')
        self.stime = int(time.time())

        # Check for new version.
        #self._nver = self.__getlatestversion()
        #self._cver = self.cfg.getvalue('upd', 'version')
        #if self._nver[0]:
        #    logger.warning(f'A new version of Kiyoko is available: {self._nver[1]}')
        #logger.info(f'Current Kiyoko version: {self._cver}')

        # Initialize discord.py bot client.
        super().__init__(
            command_prefix = self.cfg.getvalue('global', 'prefix', '/'),
            help_command   = None,
            tree_cls       = kiyo_error.KiyokoCommandTree,
            description    = 'discord application for automatization and community engagement',
            intents        = discord.Intents().all()
        )

        # Establish database connection.
        self.dbman  = kiyo_db.KiyokoDatabaseManager(self.cfg)
        # Initialize module manager.
        self.modman = kiyo_mod.KiyokoModuleManager(self)
        # Initialize guild settings manager.
        self.gcman  = kiyo_mguild.KiyokoGuildConfigManager(self)
        # Initialize resource manager.
        self.resman = kiyo_res.KiyokoResourceManager(self)


    # Reimplements the 'on_ready' event handler.
    #
    # Returns nothing.
    async def on_ready(self) -> None:
        # Sync database.
        await kiyo_mguild.syncdb(self)
        # Load guild configs.
        await self.gcman.loadgconfig()
        # Load modules.
        await self.modman.loadmodules()

        ## We are done setting things up and are now ready.
        logger.info(f'Kiyoko is now available as \'{self.user}\'. Ready.')


    # Starts the app's main-loop.
    #
    # Returns nothing.
    def runapp(self) -> None:
        self.run(
            token     = str(self.cfg.getvalue(None, 'token')),
            reconnect = bool(self.cfg.getvalue('global', 'reconnect', True))
        )


    # This event handler is triggered whenever there is an exception
    # thrown inside another event handler.
    #
    # Returns nothing.
    async def on_error(self, event, *args, **kwargs) -> None:
        # Just log the error using our logger for now.
        logger.error(traceback.format_exc())


    # This event handler processes message commands only.
    #
    # Returns nothing.
    async def on_message(self, msg: discord.Message) -> None:
        await self.process_commands(msg)


    # Checks for a new version by searching the official repository's 'env' file.
    #
    # Returns a tuple containing the latest version and a boolean value describing
    # whether the version found is newer than the version of this application.
    def __getlatestversion(self) -> tuple[bool, str]:
        # Get required data.
        nver = ''
        cver = self.cfg.getvalue('upd', 'version')
        url  = 'https://raw.githubusercontent.com/TophUwO/Kiyoko/master/conf/.env'

        # Get the latest '.env' file containing the version number of the current
        # 'master' branch.
        with req.urlopen(url) as tmp_file:
            cfg = configparser.ConfigParser()
            cfg.read_string(tmp_file.read().decode('utf-8'))

            nver = cfg['upd']['version']

        # Return latest version and whether the current version is
        # outdated.
        return (
            vcmp.StrictVersion(nver) > vcmp.StrictVersion(cver),
            nver
        )


    # Initializes the logging facility.
    #
    # Returns nothing.
    def __initlogging(self) -> None:
        logdir = 'logs'
        fname  = 'log_{time:MM-DD-YYYY_HHmmss}.log'
        fmt    = '[{time:MM-DD-YYYY HH:mm:ss}] <lvl>{level:<8}</> {module}: {message}'
        rot    = '00:00'
        ret    = '14 days'

        # Create 'log' directory if it does not exist.
        try:
            if not os.path.exists(logdir):
                os.mkdir(logdir)
        except Exception as tmp_e:
            logger.critical(f'Failed to create log directory \'{logdir}\'. Reason: {tmp_e}')

            raise
      
        # Setup loguru.
        logger.remove()
        logger.level('WARNING', color='<yellow>')
        logger.add(sys.stderr, format = fmt, colorize = True)
        logger.add(logdir + '/' + fname, format = fmt, rotation = rot, retention = ret)

        # Everything went well.
        logger.success('Successfully initialized logging facility.')


