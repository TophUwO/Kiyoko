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

# This file implements the client.

# imports
from ast import Try
import logging
import discord
import os
import init as sj_init


# This class reimplements certain aspects of the event handlers, etc.
class SukajanClient(discord.Client):
    def __init__(self):
        # Let discord.py do its default initialization.
        super().__init__(intents=discord.Intents.all())

        # Setup logging.
        logging.root.setLevel(logging.NOTSET)
        
        # Load configuration file.
        try:
            self.cfg = sj_init.SukajanConfig()

            if self.cfg.getvalue('token', None) is None:
                raise Exception('Failed to retrieve token from configuration file.')
        except Exception as tmp_e:
            logging.critical(f'Failed to load configuration settings. Desc: {tmp_e}')

            os.abort()

        # Start the mainloop of the client.
        self.run(
            token=self.cfg.getvalue('token', None),
            reconnect=self.cfg.getvalue('reconnect', True)
        )


    def __del__(self):
        # Write config file on program exit.
        self.cfg.writeconfig()


    # Reimplements the 'on_ready' event handler.
    async def on_ready(self) -> None:
        logging.info(f'SukajanBot is now available as "{self.user}". Ready.\n')


    # Reimplements the 'on_message' event handler.
    async def on_message(self, message: discord.Message) -> None:
        # Ignore messages sent by bots.
        if message.author.bot:
            return

        # Send a temporary 'Hello, world!' message.
        await message.channel.send('Hello, world!')


