######################################################################
# Project:    Sukajan Bot v0.1                                       #
# File Name:  init.py                                                #
# Author:     Sukajan One-Trick <tophuwo01@gmail.com>                #
# Description:                                                       #
#   a bot for the KirikoMains subreddit for advanced custom          #
#   features required by the moderation team                         #
#                                                                    #
# (C) 2023 Sukajan One-Trick. All rights reserved.                   #
######################################################################

# This file implements the init module, managing configuration resources
# and constants.

# imports
import json
import jsonschema
import discord
import logging
import datetime


# JSON config file output name template
sj_outfiletempl = 'backups/cfgbackup_{}_{}-{}-{}_{}{}{}.json'


# This class holds all configuration options the bot supports alongside
# bot-wide constants.
class SukajanConfig:
    # constants and default settings
    sj_const_defbotname    = 'SukajanBot'
    sj_const_definitfile   = 'conf/init.json'
    sj_const_defstatus     = discord.Status.online
    sj_const_defautoreconn = True
    sj_const_defprefix     = '/'
    sj_const_defavatar     = 'conf/avatars/def.png'

    # Initializes the configuration class, providing a file used
    # to read settings.
    #
    # Returns nothing.
    def __init__(self, initfile: str = ''):
        # settings variables
        self.conf_botname       = None
        self.conf_status        = None
        self.conf_autoreconnect = None
        self.conf_prefix        = None
        self.conf_token         = None
        self.conf_avatar        = None

        # Attempt to load the config.
        self.loadconfig(path=initfile, reset=True)


    # Loads a configuration file and updates all found configuration
    # found within it. The format of the config file is JSON.
    # If the specified file does not exist or is invalid, the function
    # resets the configuration to default values.
    #
    # Return values:
    #     0 - reset config to default
    #     1 - update config successfully
    #     2 - error (IO, JSON decoding, etc.)
    #     3 - no action was performed
    def loadconfig(self, path: str, reset: bool = False) -> int:
        # Fix the path in case it is an empty file path.
        path = path if path.__len__() > 0 else SC.sj_const_definitfile

        # Attempt to open the config file. If that fails, try
        # the fallback route by loading default settings if
        # requested, otherwise do nothing.
        try:
            logging.info(f'Attempt loading config file "{path}".')

            with open(path, 'r') as tmp_file:
                # Validate JSON config file.
                tmp_json = json.load(tmp_file)

                # Read properties and set config values accordingly.
                logging.info(f'JSON config file \"{path}\" valid. Updating configuration.')

                self.conf_prefix        = tmp_json['prefix']
                self.conf_autoreconnect = bool(tmp_json['reconnect'])
                self.conf_botname       = tmp_json['alias']
                self.conf_status        = tmp_json['status']
                self.conf_token         = tmp_json['token']
                self.conf_avatar        = tmp_json['avatar']

                return 1
        except Exception as tmp_e:
            logging.error(f'File "{path}" not found or there was an error. Description: {tmp_e}.')
            if reset:
                logging.info('Use default configuration instead.')

            # Load default config if requested.
            if reset:
                self.loaddefconfig()
            return 0 if reset else 3



    # Loads the default configuration of the bot.
    #
    # Returns nothing.
    def loaddefconfig(self) -> None:
        self.conf_botname       = SC.sj_const_defbotname
        self.conf_autoreconnect = SC.sj_const_defautoreconn
        self.conf_prefix        = SC.sj_const_defprefix
        self.conf_status        = SC.sj_const_defstatus

        # Send confirmation log message.
        logging.info('Default configuration has been loaded.')


    # Writes the configuration to the file specified.
    # If the file already exists, it will be overwritten.
    #
    # Returns True on success, False on failure.
    def writeconfig(self, user: discord.User = None) -> bool:
        # Get current date and time.
        tmp_dt = datetime.datetime.now()

        # Format file name.
        fname_formatted = SC.sj_const_definitfile if user == None else sj_outfiletempl.format(
            user.name,
            tmp_dt.month,
            tmp_dt.day,
            tmp_dt.year,
            tmp_dt.hour,
            tmp_dt.minute,
            tmp_dt.second
        )

        # Create and populate JSON object, representing current
        # settings.
        tmp_jsonobj = json.loads(f'''
            {{
                "alias":     "{self.conf_botname}",
                "token":     "{self.conf_token}",
                "reconnect":  {int(self.conf_autoreconnect)},
                "status":    "{self.conf_status}",
                "prefix":    "{self.conf_prefix}"
            }}
        ''')

        # Open and write file.
        try:
            with open(fname_formatted, 'w') as tmp_outfile:
                # Write the created JSON object to the file.
                tmp_outfile.write(json.dumps(obj=tmp_jsonobj, indent=4))

                logging.info(f'Successfully wrote configuration file [fname="{fname_formatted}"].')
                return True
        except Exception as tmp_e:
            logging.error(f'Could not write configuration file. Description: {tmp_e}.')

            return False



# Make shorter alias for readability purposes.
SC = SukajanConfig


