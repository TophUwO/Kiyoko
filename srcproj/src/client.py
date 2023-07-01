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
import math
import config as sj_cfg
import db as sj_db


# This class reimplements certain aspects of the event handlers, etc.
class SukajanClient(discord.Client):
    def __init__(self):
        # Let discord.py do its default initialization.
        super().__init__(intents=discord.Intents.all())
        self._gcfg = dict()

        # Setup logging.
        logging.root.setLevel(logging.NOTSET)
        
        # Load configuration file.
        try:
            self._cfg = sj_cfg.SukajanConfig()

            if self._cfg.getvalue('token') is None:
                raise Exception('Failed to retrieve token from configuration file.')
        except Exception as tmp_e:
            logging.critical(f'Failed to load configuration settings. Desc: {tmp_e}')

            os.abort()

        # Establish database connection.
        dbpath = self._cfg.getvalue('db')
        try:
            self._db = sj_db.SukajanDatabase(dbpath, self._cfg)
        except Exception as tmp_e:
            logging.critical(f'Could not establish database connection to database "{dbpath}". Desc: {tmp_e}')

            os.abort()

        # Start the mainloop of the client.
        self.run(
            token=self._cfg.getvalue('token', None),
            reconnect=self._cfg.getvalue('reconnect', True)
        )


    # Applies global settings on startup.
    async def __applyglobalsettings(self) -> None:
        # Apply global bot account settings.
        try:
            with open(self._cfg.getvalue('avatar'), 'rb') as tmp_avatar:
                await self.user.edit(
                    username=self._cfg.getvalue('alias'),
                    avatar=tmp_avatar.read()
                )
        except Exception as tmp_e:
            logging.error(f'Failed to apply global application settings. Desc: {tmp_e}')

            return

        # Everything went well.
        logging.info('Successfully applied global settings.')


    # Applies guild-specific member settings when the bot goes online.
    #
    # Returns nothing.
    async def __applyguildsettings(self, guild: discord.Guild, settings: sj_cfg.SukajanGuildConfig) -> None:
        # Get member entry for bot.
        member = guild.get_member(self.user.id)

        # Modify settings.
        try:
            await member.edit(nick=settings.alias)
        except Exception as tmp_e:
            logging.error(f'Failed to apply guild settings for "{guild.name}" (id: {guild.id}). Desc: {tmp_e}')

            return

        # Everything went well.
        logging.info(f'Successfully applied settings for guild "{guild.name}" (id: {guild.id}).')


    # Reimplements the 'on_ready' event handler.
    async def on_ready(self) -> None:
        # Apply global settings.
        await self.__applyglobalsettings()

        # Fetch guild settings for all guilds he bot is connected to.
        for tmp_guild in self.guilds:
            ginfo = self._db.execquery(f'SELECT * from guildconfig WHERE guildid = \'{tmp_guild.id}\'', 1)

            # Generate guild config object and put it into the dictionary.
            try:
                # Store guild settings in dictionary (to reduce db calls)
                self._gcfg[tmp_guild.id] = sj_cfg.SukajanGuildConfig(ginfo)

                # Apply guild settings.
                await self.__applyguildsettings(tmp_guild, self._gcfg[tmp_guild.id])

                logging.info(f'Successfully loaded configuration for guild "{tmp_guild.name}" (id: {tmp_guild.id})')
            except Exception as tmp_e:
                logging.error(f'Could not load configuration for guild {tmp_guild.name} (id: {tmp_guild.id}). Desc: {tmp_e}')

        # We are done setting things up and are now ready.
        logging.info(f'SukajanBot is now available as "{self.user}". Ready.')


    # Reimplements the 'on_create' event handler.
    # This handler is executed when
    #     (1) the bot creates a guild
    #     (2) the bot joins a guild
    #
    # Returns nothing.
    async def on_guild_join(self, guild: discord.Guild) -> None:
        # Convert 'created_at' time to UNIX timestamp (epoch).
        tmp_ts = math.floor(guild.created_at.timestamp())

        # Add guild info to the bots database.
        self._db.execcommand(f'INSERT INTO guilds VALUES({guild.id}, {guild.owner_id}, {tmp_ts})')
        self._db.execcommand(f'INSERT INTO guildconfig (guildid) VALUES({guild.id})')
        self._db.flush()

        # Add guild info to dict.
        tmp_ginfo = self._db.execquery(f'SELECT * FROM guildconfig WHERE guildid = \'{guild.id}\'')
        self._gcfg[guild.id] = sj_cfg.SukajanGuildConfig(tmp_ginfo)

        msg = 'Created and joined' if guild.owner_id == self.user.id else 'Joined'
        logging.info(f'{msg} guild "{guild.name}" (id: {guild.id}).')


    # Reimplements the 'on_guild_remove' event handler.
    # This handler is executed when
    #    (1) the bot leaves the guild
    #    (2) the bot is kicked/banned from the guild
    #    (3) the guild is deleted by the owner
    #
    # Returns nothing.
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        # Remove guild info from the database.
        self._db.execcommand(f'DELETE FROM guilds where id={guild.id}')
        self._db.execcommand(f'DELETE FROM guildconfig WHERE guildid={guild.id}')
        self._db.flush()

        # Remove guild info from dict.
        self._gcfg.pop(guild.id)

        logging.info(f'Left guild "{guild.name}" (id: {guild.id}).')


    # Reimplements the 'on_message' event handler.
    async def on_message(self, message: discord.Message) -> None:
        # Ignore messages sent by bots.
        if message.author.bot:
            return

        # Send a temporary 'Hello, world!' message.
        await message.channel.send('Hello, world!')


