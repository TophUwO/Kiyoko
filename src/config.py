######################################################################
# Project:    Sukajan Bot v0.1                                       #
# File Name:  config.py                                              #
# Author:     Sukajan One-Trick <tophuwo01@gmail.com>                #
# Description:                                                       #
#   a bot for the KirikoMains subreddit for advanced custom          #
#   features required by the moderation team                         #
#                                                                    #
# (C) 2023 Sukajan One-Trick. All rights reserved.                   #
######################################################################

# This file implements the config module, managing configuration resources
# and constants.

# imports
from loguru import logger
import dotenv


# Raise this exception if the token is somehow invalid.
class TokenError(Exception):
    pass


# This class holds all configuration options the bot supports alongside
# bot-wide constants.
class SukajanConfig(object):
    def __init__(self, path: str):
        # Init attribs.
        self._changed = False
        self._object  = dict()
        self._token   = ''
        self._path    = path

        # Load config file.
        self.readconfig(path)


    def __del__(self):
        # Write-back config if it has changed.
        if self._changed:
            self.writeconfig(self._path)


    # Retrieves a value from the internal settings object. If the key
    # does not exist, return '*fallback*.
    #
    # Returns value associated with *key*, otherwise *fallback*.
    def getvalue(self, key: str, fallback: any = None) -> any:
        if key == 'token':
            return self._token

        return self._object.get(key, fallback)

    
    # Updates the configuration of the given *key* with *value*.
    # If the key does not exist, create a new one. If the key did
    # not exist previously, the function returns None.
    #
    # Returns old value.
    def setvalue(self, key: str, value: any) -> any:
        # Get old value.
        oldval = self._object.get(key, None)

        # Update value and internal state.
        self._object[key] = value
        self._changed     = True

        return oldval


    # Reads the config file specified by *fname*.
    # The internal settings object is updated.
    # 
    # Returns nothing.
    def readconfig(self, fname: str) -> None:
        # Load global settings.
        try:
            self._object = dotenv.dotenv_values(fname)
        except:
            logger.error(f'Failed to read global configuration from \'{fname}\' file.')

            raise

        # Load token.
        tokenpath = self.getvalue('tokenpath') 
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
    def writeconfig(self, fname: str) -> None:
        if self._changed == False:
            return

        # Write all values.
        try:
            with open(fname, 'w') as tmp_file:
                for key, value in self._object.items():
                    tmp_file.write(f'{key} = {value}\n')
        except:
            logger.error(f'Failed to write to configuration file \'{fname}\'.')

            raise

        # Everything went well.
        self._changed = False
        logger.success('Successfully wrote global configuration to file.')



# This class, as opposed to SukajanConfig holds guild-specific
# configuration settings.
class SukajanGuildConfig(object):
    def __init__(self, settings: tuple):
        if settings is None:
            raise Exception('Invalid "settings" tuple.')

        # Settings are provided in this order: (guildid, prefix, alias, logchan, welcomechan, goodbyechan, sendwelcome, sendgoodbye).
        self.id          = int(settings[0])
        self.pre         = settings[1]
        self.alias       = settings[2]
        self.logchan     = settings[3]
        self.welcomechan = settings[4]
        self.goodbyechan = settings[5]
        self.sendwelcome = int(settings[6])
        self.sendgoodbye = int(settings[7])


