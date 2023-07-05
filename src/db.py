################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# This file implements the database connection and bookkeeping.

# imports
import os
import sqlite3, aiosqlite
from loguru import logger

import src.config as kiyo_cfg


# Raise this exception if the database is in an invalid state.
class DatabaseConnectionError(Exception):
    def __init__(self):
        self.message = 'Invalid database connection object.'


# This class holds the database connection.
class KiyokoDatabaseManager(object):
    def __init__(self, cfg: kiyo_cfg.KiyokoGlobalConfig):
        # Get required settings from config.
        dbdir    = cfg.getvalue('dbdir')
        dbpath   = dbdir + '/' + cfg.getvalue('dbfile')
        dbschema = cfg.getvalue('dbschemapath')

        # Init attributes.
        self._path = dbpath

        # Open database connection.
        # If the file does not yet exist, create it and set everything up.
        direxists = os.path.exists(dbdir)
        dbexists  = os.path.exists(dbpath)
        if not direxists or not dbexists:
            logger.debug(f'Could not find "{dbpath}". Creating it ...')

            self.__createdb(dbschema, direxists, dbdir)
        else:
            logger.debug(f'Found database file: \'{dbpath}\'.')

        # Database is ready.
        logger.success(f'Database \'{dbpath}\' ready. aiosqlite version: {aiosqlite.sqlite_version}')


    # Opens a new connection to the internal database.
    #
    # Returns connection object.
    async def newconn(self) -> aiosqlite.Connection:
        return await aiosqlite.connect(self._path)


    # Executes an SQL command with no return value.
    #
    # Returns nothing.
    async def execcommand(self, conn: aiosqlite.Connection, cmd: str, flush: bool = False) -> None:
        await self.__execquery(conn, cmd, 0, 0)

        if flush:
            await conn.commit()


    # Executes an SQL query.
    #
    # Returns query result.
    async def execquery(self, conn: aiosqlite.Connection, cmd: str, n: int) -> any:
        return await self.__execquery(conn, cmd, n, 1)


    # Create the database structure using a specified schema.
    # The resulting database is empty but ready for use.
    #
    # Returns nothing, but throws an exception in case of an
    # error.
    def __createdb(self, schemapath: str, direxists: bool, dbdir: str) -> None:
        # Create database directory if it does not exist.
        if not direxists:
            os.mkdir(dbdir)

        # Create the database by attempting to connect to it.
        conn = None
        try:
            conn = sqlite3.connect(self._path)
        except:
            logger.error(f'Failed to create database \'{self._path}\'')

            raise

        # Run SQL script specified in .env for creating the
        # database.
        # Check if schema file exists.
        try:
            with open(schemapath, 'r') as tmp_fschema:
                conn.executescript(tmp_fschema.read())
        except:
            logger.error(f'Failed to execute SQL script \'{schemapath}\'.')

            raise

        # If everything went well, we should arrive here.
        conn.close()
        logger.success(f'Successfully created database \'{self._path}\'.')


    # Executes a query on behalf of the client.
    # n:
    #     0  - fetch all
    #     1  - fetch one
    #     x  - fetch many
    #
    # Returns nothing, but throws an exception in case of an
    # error.
    async def __execquery(self, conn: aiosqlite.Connection, cmd: str, n: int = 0, mode: int = 0) -> list:
        if conn is None:
            raise DatabaseConnectionError

        # Execute command.
        await conn.execute(cmd)
        cur = await conn.cursor()

        # Fetch results from db.
        tmp_res = None
        if n < 0:
            return None
        match n:
            case 0: tmp_res = await cur.fetchall()
            case 1: tmp_res = await cur.fetchone()
            case _: tmp_res = await cur.fetchmany(n)

        # Close cursor and return result.
        await cur.close()
        return None if mode == 0 else tmp_res


