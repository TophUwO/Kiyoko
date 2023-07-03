################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# This file implements the database connection and bookkeeping.

# imports
import os
import sqlite3
from loguru import logger

import src.config as kiyo_cfg


# Raise this exception if the database is in an invalid state.
class DatabaseStateError(Exception):
    pass


# This class holds the database connection.
class KiyokoDatabaseManager(object):
    def __init__(self, cfg: kiyo_cfg.KiyokoGlobalConfig):
        # Get required settings from config.
        dbdir    = cfg.getvalue('dbdir')
        dbpath   = dbdir + '/' + cfg.getvalue('dbfile')
        dbschema = cfg.getvalue('dbschemapath')

        # Open database connection.
        # If the file does not yet exist, create it and set everything up.
        direxists = os.path.exists(dbdir)
        dbexists  = os.path.exists(dbpath)
        if not direxists or not dbexists:
            logger.debug(f'Could not find "{dbpath}". Creating it ...')

            self.__createdb(dbpath, dbschema, direxists, dbdir)
        else:
            logger.debug(f'Found database file: \'{dbpath}\'.')

        # Establish connection. If this fails, an exception will be raised.
        try:
            self._conn = sqlite3.connect(dbpath)
            self._cur  = self._conn.cursor()
        except:
            logger.error(f'Failed to connect to database \'{dbpath}\'.)')

            raise

        # Everything was successful.
        logger.success(f'Successfully established connection to database \'{dbpath}\'. SQLite3 version: {sqlite3.version}')


    def __del__(self):
        # Close database connection.
        if self._conn is None:
            return

        self._conn.commit()
        self._conn.close()


    # Executes a query on behalf of the client.
    # n:
    #     0  - fetch all
    #     1  - fetch one
    #     x  - fetch many
    #
    # Returns nothing, but throws an exception in case of an
    # error.
    def __execquery(self, cmd: str, n: int = 0, mode: int = 0) -> list:
        # If the connection has not yet been established,
        # do nothing.
        if self._conn is None:
           raise DatabaseStateError

        # Execute command.
        self._cur.execute(cmd)

        # Fetch results from db.
        tmp_res = None
        if n < 0:
            return None
        match n:
            case 0: tmp_res = self._cur.fetchall()
            case 1: tmp_res = self._cur.fetchone()
            case _: tmp_res = self._cur.fetchmany(n)

        return None if mode == 0 else tmp_res


    # Executes an SQL command with no return value.
    #
    # Returns nothing.
    def execcommand(self, cmd: str, flush: bool = False) -> None:
        self.__execquery(cmd, 0, 0)

        if flush:
            self._conn.commit()


    # Executes an SQL query.
    #
    # Returns query result.
    def execquery(self, cmd: str, n: int) -> any:
        return self.__execquery(cmd, n, 1)


    # Flushes the database. Call after inserts and updates.
    #
    # Returns nothing.
    def flush(self) -> None:
        if self._conn is None:
            raise DatabaseStateError

        self._conn.commit()


    # Create the database structure using a specified schema.
    # The resulting database is empty but ready for use.
    #
    # Returns nothing, but throws an exception in case of an
    # error.
    def __createdb(self, path: str, schemapath: str, direxists: bool, dbdir: str) -> None:
        # Create database directory if it does not exist.
        if not direxists:
            os.mkdir(dbdir)

        # Create the database by attempting to connect to it.
        try:
            self._conn = sqlite3.connect(path)
        except:
            logger.error(f'Failed to create database \'{path}\'')

            raise

        # Run SQL script specified in .env for creating the
        # database.
        # Check if schema file exists.
        try:
            with open(schemapath, 'r') as tmp_fschema:
                self._conn.executescript(tmp_fschema.read())
        except:
            logger.error(f'Failed to execute SQL script \'{schemapath}\'.')

            raise

        # If everything went well, we should arrive here.
        self._conn.close()
        logger.success(f'Successfully created database \'{path}\'.')


