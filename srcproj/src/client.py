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
import discord
import os
import init as sj_init


# This class eimplements certain aspects of the event handlers, etc.
class SukajanClient(discord.Client):
    def __init__(self):
        # Let discord.py do its default initialization.
        super().__init__(intents=discord.Intents.all())

        # Setup logging, load and apply config.
        logging.root.setLevel(logging.NOTSET)
        self.config = sj_init.SukajanConfig('')

        # If the token could not be retrieved, terminate bot.
        if self.config.conf_token == None:
            logging.critical('Could not read token; terminating application.')

            exit()

        # Start the mainloop of the client.
        self.run(token=self.config.conf_token, reconnect=self.config.conf_autoreconnect)

    def __del__(self):
        # Write config file if it does not exist.
        if not os.path.exists(self.config.sj_const_definitfile):
            self.config.writeconfig(user=None)


    # Applies the current configuration; should be called
    # after the configuration was changed/loaded/reset, etc.
    #
    # Returns nothing.
    async def updateconfig(self) -> None:
        await self.change_presence(status=self.config.conf_status)
        await self.user.edit(username=self.config.conf_botname)

        # Load new avatar.
        try:
            with open(self.config.conf_avatar, 'rb') as tmp_av:
                await self.user.edit(avatar=tmp_av.read())
        except Exception as tmp_e:
            logging.error(f'Could not open avatar image file "{self.config.conf_avatar}". Description: {tmp_e}.')


    # Reimplements the 'on_ready' event handler.
    async def on_ready(self) -> None:
        # Apply bot account settings if they vary from the default
        # settings.
        await self.updateconfig()

        logging.info(f'SukajanBot is now available as "{self.user}". Ready.\n')


    # Reimplements the 'on_message' event handler.
    async def on_message(self, message: discord.Message) -> None:
        # Ignore messages sent by the bot itself.
        if message.author == self.user:
            return

        # Send a temporary 'Hello, world!' message.
        await message.channel.send('Hello, world!')


