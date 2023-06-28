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
import os
import discord
import logging


# This class holds all configuration options the bot supports alongside
# bot-wide constants.
class SukajanConfig:
    # constants and default settings
    sj_const_defbotname    = 'SukajanBot'
    sj_const_definitfile   = './init.json'
    sj_const_defstatus     = discord.Status.online
    sj_const_autoreconnect = True

    # Initializes the configuration class, providing a file used
    # to read settings.
    #
    # Returns nothing.
    def __init__(self, initfile: str = ''):
        # settings variables
        self.conf_botname       = None
        self.conf_status        = None
        self.conf_autoreconnect = None

        # Attempt to load the config.
        res = self.loadconfig(initfile)


    # Loads a configuration file and updates all found configuration
    # found within it. The format of the config file is JSON.
    # If the specified file does not exist or is invalid, the function
    # resets the configuration to default values.
    #
    # Return values:
    #     0 - reset config to default
    #     1 - update config successfully
    #     2 - error (IO, JSON decoding, etc.)
    def loadconfig(self, path: str) -> int:
        pass


    # Loads the default configuration of the bot.
    #
    # Returns nothing.
    def loaddefconfig(self):
        self.conf_botname = SukajanConfig.sj_const_defbotname


    # Writes the configuration to the file specified.
    # If the file already exists, it will be overwritten.
    #
    # Returns True on success, False on failure.
    def writeconfig(self) -> bool:
        pass


