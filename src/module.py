################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# module.py - module ('extension') management

# imports
import os
import discord.ext.commands as commands

from loguru import logger



# Raise this exception if required modules could not be
# loaded.
class RequiredModuleError(Exception):
    def __init__(self, mods: list):
        self.message = f'Failed to load {len(mods)} modules: {mods}.'


# Base class for all Cogs, use this to not have to write the
# constructor for every Cog you create.
class KiyokoModule_Base(commands.Cog):
    def __init__(self, app):
        self._app = app



# class representing the module manager, handles (un-)loading of modules
# as well as errors arising from the module (un-)loading process.
class KiyokoModuleManager(object):
    def __init__(self, app):
        self._app   = app
        self._lmods = list()


    # Returns a list of all loaded modules.
    #
    # Returns module list.
    def getloadedmodules(self) -> list:
        return self._lmods


    # Loads all modules that are present in the 'moduledir' specified
    # by .env.
    # If the 'reqmodules' field is present and contains values, this
    # method will raise an exception if any of the specified modules
    # could not be loaded for whatever reason.
    #
    # Returns nothing.
    async def loadmodules(self) -> None:
        # Print opening debug message.
        logger.debug('Begin loading modules ...')

        # Obtain required config.
        modext    = '.py'
        moddir    = self._app.cfg.getvalue('global', 'moduledir')
        reqmods   = self._app.cfg.getvalue('global', 'reqmodules', '').split(',')
        moddirfmt = (moddir + '.').replace('/', '.')

        # Strip list elements of any trailing spaces, so that 'x, y' is also
        # just as valid as 'x,y'.
        reqmods = [elem.strip(' ') for elem in reqmods] 

        # Check if module directory exists and whether there are any
        # modules to load.
        mods2load = [] if not os.path.exists(moddir) else [elem[:-len(modext)] for elem in os.listdir(moddir) if elem.endswith(modext)]
        if len(mods2load) == 0:
            logger.info('No modules to load.')

            return

        # Load all modules present in that directory.
        for tmp_fname in mods2load:
            modpath = moddirfmt + tmp_fname

            # Load module.
            try:
                await self._app.load_extension(modpath)
            except Exception as tmp_e:
                logger.error(f'Failed to load module \'{tmp_fname}\' (path: \'{modpath}\'). Reason: {tmp_e}')

                continue

            # Remove module from the 'reqmods' list if present and add 
            # the module to the list of loaded modules. Also take care
            # of the edge-case if there are multiple occurences of the
            # same element in the list.
            if tmp_fname in reqmods:
                reqmods = [elem for elem in reqmods if elem != tmp_fname]
            self._lmods.append(tmp_fname)

        # Raise an exception if there are still modules that are required
        # but could not be loaded.
        if len(reqmods) > 0:
            raise RequiredModuleError(reqmods)

        # Everything went well.  
        logger.debug('Finished loading modules.')


    # Syncs the command tree to all guilds the client is connected
    # to.
    #
    # Returns nothing.
    async def synccmdtree(self) -> None:
        iserr = False
        for guild in self._app.guilds:
            try:
                await self._app.tree.sync(guild = guild)
            except Exception as tmp_e:
                logger.error(f'Failed to sync command tree to guild "{guild.name}" (id: {guild.id}). Desc: {tmp_e}')

                iserr = True
                continue

        # Everything went well.
        if not iserr:
            logger.success('Successfully synced command tree to Discord.')


