######################################################################
# Project:    Sukajan Bot v0.1                                       #
# File Name:  db.py                                                #
# Author:     Sukajan One-Trick <tophuwo01@gmail.com>                #
# Description:                                                       #
#   a bot for the KirikoMains subreddit for advanced custom          #
#   features required by the moderation team                         #
#                                                                    #
# (C) 2023 Sukajan One-Trick. All rights reserved.                   #
######################################################################

# This file implements the database connection and bookkeeping.

# imports
import logging
import os
import sqlite3
import config as sj_config


# This class holds the database connection.
class SukajanDatabase(object):
    def __init__(self, path: str, cfg: sj_config.SukajanConfig):
        # If path is invalid, abort.
        if path is None or path == '':
            raise Exception('Invalid or empty database path.')

        # Open database connection.
        # If the file does not yet exist, create it and set everything up.
        dbexists = os.path.exists(path)
        if not dbexists:
            logging.warning(f'Database "{path}" does not exist. Creating it ...')

            try:
                self.__createdb(path, cfg)
            except Exception as tmp_e:
                logging.critical(f'Could not create database infrastructure {path}. Desc: {tmp_e}')

                # Reraise the exception so that the client class can
                # abort the application.
                raise
        else:
            logging.info(f'Found database file: "{path}".')

        # Establish connection. If this fails, an exception will be raised.
        self._conn = sqlite3.connect(path)
        if self._conn is None:
            raise Exception(f'Failed to connect to database "{path}".')
        self._cur = self._conn.cursor()

        # Everything was successful.
        logging.info(f'Successfully established connection to database "{path}". SQLite3 version: {sqlite3.version}')


    def __del__(self):
        # Close database connection.
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
           return

        # Execute command.
        try:
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
        except Exception as tmp_e:
            logging.error(f'Failed to execute SQL command "{cmd}". Desc: {tmp_e}')

        return None


    # Executes an SQL command with no return value.
    #
    # Returns nothing.
    def execcommand(self, cmd: str) -> None:
        self.__execquery(cmd, 0, 0)


    # Executes an SQL query.
    #
    # Returns query result.
    def execquery(self, cmd: str, n: int) -> any:
        return self.__execquery(cmd, n, 1)


    # Flushes the database. Call after inserts and updates.
    #
    # Returns nothing.
    def flush(self) -> None:
        self._conn.commit()


    # Create the database structure if it has not yet been created.
    # The resulting database is empty but ready for use.
    #
    # Returns nothing, but throws an exception in case of an
    # error.
    def __createdb(self, path: str, cfg: sj_config.SukajanConfig) -> None:
        # Create the database by attempting to connect to it.
        self._conn = sqlite3.connect(path)
        self._cur = self._conn.cursor()
        if self._conn is None:
            raise Exception(f'Failed to create database "{path}".')

        # Create GUILDS table (primary key 'id')
        # Fields:
        #     (pk) id      - guild id
        #          name    - guild name
        #          ownerid - id of the guild owner
        #          created - time it was created 
        self._cur.execute(
            '''CREATE TABLE IF NOT EXISTS guilds(
                id      VARCHAR(256) NOT NULL,
                ownerid VARCHAR(256) NOT NULL,
                created INTEGER NOT NULL,

                PRIMARY KEY(id)
            )'''
        )
        
        # Create GUILDCONFIG table
        # Fields:
        #     (fk) guildid - id the of the guild the setting belongs to
        #          prefix  - command prefix
        #          alias   - alias the bot will use on that guild
        #          avatar  - URL of the avatar the bot will use on that guild
        #          logchan - id of the modlog channel
        self._cur.execute(
            f'''CREATE TABLE IF NOT EXISTS guildconfig(
                guildid VARCHAR(256) NOT NULL,
                prefix VARCHAR(10) DEFAULT '{cfg.getvalue('prefix')}',
                alias VARCHAR(256) DEFAULT '{cfg.getvalue('alias')}',
                logchan VARCHAR(256),

                PRIMARY KEY(guildid)
            )'''
        )

        # Close connection once we are done and print info message.
        self._conn.close()
        logging.info(f'Successfully created database "{path}".')


