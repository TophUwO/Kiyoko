################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# config.py - managing global and guild-specific configuration

# imports
import time, dataclasses
import configparser, asyncio

from dataclasses import dataclass
from loguru      import logger
from typing      import Self

import discord.ext.tasks as tasks

import src.utils as kiyo_utils



# Raise this exception if the token is somehow invalid.
class TokenError(Exception):
    pass

# Raise this exception if there are keys missing in the config file.
class ConfigError(Exception):
    pass


# This class holds all configuration options the bot supports alongside
# bot-wide constants.
class KiyokoGlobalConfig(object):
    def __init__(self, path: str):
        # Init attribs.
        self._changed = False
        self._token   = ''
        self._path    = path
        self._parser  = configparser.ConfigParser() 

        # Load config file.
        self.readconfig(path)

        # Validate config.
        if not self.__validateconfig():
            raise ConfigError('\'.env\' file is malformed (missing or empty keys?).')


    def __del__(self):
        # Write-back config if it has changed.
        if self._changed:
            self.writeconfig(self._path)


    # Retrieves a value from the internal settings object. If the path
    # does not exist, return *fallback*.
    #
    # Returns value associated with *key*, otherwise *fallback*.
    def getvalue(self, section: str, key: str, fallback: any = None) -> any:
        if section is None and key == 'token':
            return self._token

        return self._parser.get(section, key, fallback = fallback)


    # Creates a generator that returns all keys in the 'global' section.
    #
    # Returns generator.
    def globalkeys(self) -> str:
        for key in self._parser['global'].keys():
            yield key

    
    # Updates the configuration of the given *key* with *value*.
    # If the key does not exist, create a new one. If the key did
    # not exist previously, the function returns None.
    #
    # Returns old value.
    def setvalue(self, section: str, key: str, value: any) -> any:
        # Get old value.
        oldval = self.getvalue(section, key)

        # Update value and internal state.
        self._parser.set(section, key, str(value))
        self._changed = True

        return oldval


    # Reads the config file specified by *fname*.
    # The internal settings object is updated.
    # 
    # Returns nothing.
    def readconfig(self, fname: str) -> None:
        # Load global settings.
        try:
            self._parser.read(fname)
        except:
            logger.error(f'Failed to read global configuration from \'{fname}\'.')

            raise

        # Load token.
        tokenpath = self.getvalue('global', 'tokenpath') 
        try:
            with open(tokenpath, 'r') as tmp_tfile:
                self._token = tmp_tfile.read()

            # Check if token is not invalid.
            if self._token is None or self._token == '':
                raise TokenError('Token is invalid.')
        except:
            logger.error(f'Failed to retrieve token from \'{tokenpath}\' file.')

            raise

        # Everything went well.
        logger.success('Successfully loaded global configuration.')


    # Writes the current configuration to the ".env" file.
    #
    # Returns True on success, False on failure.
    def writeconfig(self, fname: str = None) -> None:
        if self._changed == False:
            return
        fname = fname or 'conf/.env'

        # Write all values.
        try:
            with open(fname, 'w') as tmp_file:
                self._parser.write(tmp_file)
        except:
            logger.error(f'Failed to write to configuration file \'{fname}\'.')

            raise

        # Everything went well.
        self._changed = False
        logger.success(f'Successfully wrote global configuration to file \'{fname}\'.')


    # Validates the dictionary generated from .env.
    #
    # Returns True if everything is okay, False if there
    # is an issue.
    def __validateconfig(self) -> bool:
        # Test (1): Is the 'global' section present?
        if not self._parser.has_section('global'):
            return False

        # Test (2): Are all required keys present in section 'general'?
        reqkeys = [
            'name',  'prefix', 'tokenpath', 'reconnect',
            'dbdir', 'dbfile', 'dbschemapath', 'moduledir',
            'resinitpath'
        ]
        if not all(key in self._parser['global'] for key in reqkeys):
            return False

        # Test (3): Check if any key is None or an empty string.
        #           Allow non-required fields to be empty or None.
        for opt in self._parser['global']:
            if not opt in reqkeys:
                continue
            else:
                val = self.getvalue('global', opt)

                if val is None or val == '':
                    return False

        # Everything seems to be alright.
        return True



# class representing a command info entry
@dataclass
class KiyokoCommandInfo:
    cmdname: str          # qualified (full) command name
    added:   int          # UNIX timestamp of when the command was added
    enabled: bool         # whether or not the command is globally enabled
    count:   int          # total global count of invocations
    lastuse: int          # UNIX timestamp of when the command was last invoked (globally)
    delflag: bool = False # whether or not to delete the command when the state is written the next time

    # Updates the current command info.
    # Fields that do not exist will not be updated.
    # cmdname, added cannot be updated.
    #
    # Returns the old info.
    def update(self, **kwargs) -> Self:
        old = dataclasses.replace(self)

        self.enabled = kwargs.get('enabled', self.enabled)
        self.count   = kwargs.get('count', self.count)
        self.lastuse = kwargs.get('lastuse', self.lastuse)

        return old


# class globally managing commands
class KiyokoCommandManager:
    def __init__(self, app):
        self._app = app

        # Init command info cache.
        self._changed: bool = False
        self._cache: dict[str, KiyokoCommandInfo] = dict()


    def __del__(self):
        # Write current cache to database.
        asyncio.get_event_loop().run_until_complete(self.writestate())


    # Adds a command to the cache, creating a fresh entry.
    # If an entry belonging to this command already exists, this function
    # will not do anything. To write the changes to the database, 'writestate()'
    # must be called.
    #
    # Returns nothing.
    def addcommand(self, info: KiyokoCommandInfo) -> None:
        # If a command with the given name already exists, do nothing.
        if self._cache.get(info.cmdname, None) is not None:
            return

        self._changed = True
        self._cache[info.cmdname] = info


    # Removes a command from the cache. If the command does
    # not exist, the function does nothing. To write the changes
    # to the database, 'writestate()' must be called.
    #
    # Returns old command info, or None if the command did not exist.
    def remcommand(self, cid: str) -> KiyokoCommandInfo:
        old = None
        try:
            self._cache[cid].delflag = True
            self._changed = True
        except KeyError:
            pass

        return old


    # Retrieves the info for the command with the given command ID.
    # This will never issue a database call; the data is retrieved
    # from the cache.
    #
    # Returns KiyokoCommandInfo object, or None if the command could
    # not be found.
    def getcommandinfo(self, cid: str) -> KiyokoCommandInfo:
        info = self._cache.get(cid, None)
        if info is None:
            return None

        return None if info.delflag else info


    # Updates a specific command's info. Only the given parameters will
    # be updated. If the command is not registered, the function does
    # nothing.
    #
    # Returns the old info, or None if the command is not registered.
    def updcommandinfo(self, cid: str, **kwargs) -> KiyokoCommandInfo:
        info = self._cache.get(cid, None)
        if info is None:
            return None

        self._changed = True
        return info.update(**kwargs)


    # Creates a generator that can be used to iterate over all current
    # command info entries in the cache.
    #
    # Returns generator.
    def commandinfos(self) -> KiyokoCommandInfo:
        for info in self._cache.values():
            if not info.delflag:
               yield info


    # A command that manually starts the sync background task.
    # If the task is already running, the function does nothing.
    #
    # Returns nothing.
    def startsynctask(self) -> None:
        if not self.on_flush_db.is_running():
            self.on_flush_db.start()


    # Loads the current persistent database state into the
    # command info cache.
    #
    # Returns nothing.
    async def readstate(self) -> None:
        # Establish connection to database.
        conn, cur = await self._app.dbman.newconn()

        # Read all command entries from database.
        await cur.execute('SELECT * FROM commandinfo')
        qres = await cur.fetchall()

        # Populate the cache.
        for row in qres:
            (cmdname, added, enabled, count, lastuse) = row

            # Generate command info object.
            self.addcommand(KiyokoCommandInfo(
                cmdname,
                added,
                enabled,
                count,
                lastuse
            ))

        # Close connection.
        await cur.close()
        await conn.close()


    # Writes the current cache state to the database. This should
    # be done periodically in a background task. If nothing is
    # to be written (i.e. because nothing has changed since last write),
    # this function does nothing.
    #
    # Returns nothing.
    async def writestate(self) -> None:
        if not self._changed:
            return

        # Establish database connection.
        conn, cur = await self._app.dbman.newconn()

        # Write state to table.
        sql = 'INSERT OR REPLACE INTO commandinfo VALUES(\'{}\', {}, {}, {}, {})'
        for cmd in self._cache.values():
            # Delete all command entries that have been marked as deleted before.
            if cmd.delflag:
                 await cur.execute(f'DELETE FROM commandinfo WHERE cmdname = \'{cmd.cmdname}\'')
                 
                 continue

            # Otherwise update with new state.
            await cur.execute(sql.format(cmd.cmdname, cmd.added, int(cmd.enabled), cmd.count, cmd.lastuse))

        # Flush db.
        self._changed = False
        await conn.commit()
        await cur.close()
        await conn.close()


    # Synchronizes the database and the cache with the currently registered
    # set of commands. If there are any new commands or commands that have
    # been removed before the database was last flushed, these changes will
    # now take effect.
    #
    # Returns nothing.
    async def sync(self) -> None:
        # Get list of currently registered message and application commands.
        lcmds = set([cmd.qualified_name for cmd in kiyo_utils.allcommands(self._app)])
        # Get list of commands in cache/database.
        ccmds = set([x.cmdname for x in self.commandinfos()])

        # Compile the list of commands that have to be changed (i.e. added (0), removed (1)) and
        # apply the changes.
        for (cmd, op) in [(x, 0) for x in lcmds - ccmds] + [(x, 1) for x in ccmds - lcmds]:
            if op == 0:
                # Add command to cache.
                self.addcommand(KiyokoCommandInfo(
                    cmd,
                    int(time.time()),
                    True,
                    0,
                    0
                ))
            elif op == 1:
                # Remove command from cache.
                self.remcommand(cmd)

            # Print message.
            logger.debug(f'Updated command \'{cmd}\' (op = {op}).')

        # Write updated cache to database.
        await self.writestate()


    # Task that periodically flushes the database to reflect the current state.
    #
    # Returns nothing.
    @tasks.loop(hours = 1)
    async def on_flush_db(self) -> None:
        await self.writestate()


