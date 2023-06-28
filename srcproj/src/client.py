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
import logging
from mailbox import Message
import discord
import init as sj_init


# This class eimplements certain aspects of the event handlers, etc.
class SukajanClient(discord.Client):
    def __init__(self):
        # Let discord.py do its default initialization.
        super().__init__(intents=discord.Intents.all())

        # Setup logging, load and apply config.
        logging.root.setLevel(logging.NOTSET)
        self.config = sj_init.SukajanConfig('./init.json')
        self.updateconfig()

        # Start the mainloop of the client.
        self.run(
            token='MTEyMzU3MjU2MzkxNDc4ODk0NA.GUb2kK.prOCgjy5tqNhxCyNs8taebJ7HyncC42O-pwt20',
            reconnect=self.config.conf_autoreconnect
        )


    # Applies the current configuration; should be called
    # after the configuration was changed/loaded/reset, etc.
    #
    # Returns nothing.
    def updateconfig(self) -> None:
        pass


    # Reimplements the 'on_ready' event handler.
    async def on_ready(self) -> None:
        logging.info(f'SukajanBot is now available as \"{self.user}\". Ready.\n')


    # Reimplements the 'on_message' event handler.
    async def on_message(self, message: discord.Message) -> None:
        # Ignore messages sent by the bot itself.
        if message.author == self.user:
            return

        # Send a temporary 'Hello, world!' message.
        await message.channel.send('Hello, world!')


