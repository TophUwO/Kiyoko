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
import time

import config as sj_cfg
import db as sj_db


# Generates the log file name for the current session.
#
# Returns file name string (without extention).
def genlogfname() -> str:
    # Format message.
    return time.strftime(f'log_%m-%d-%Y_%H-%M-%S')


# Sets up the logging facility.
#
# Returns nothing.
def setuplogging(dir: str) -> None:
    if dir is None:
        raise Exception('Invalid logging directory.')

    # Create 'log' directory if it does not exist.
    if not os.path.exists(dir):
        os.mkdir(dir)
    
    # Set up basic logging configuration.
    logfmt = '[%(levelname)s] %(module)s: %(message)s'
    log_handlers = [
        logging.FileHandler('./' + dir + '/' + genlogfname() + '.log', 'w', 'utf-8'),
        logging.StreamHandler()
    ]
    logging.basicConfig(level=logging.DEBUG, handlers=log_handlers, format=logfmt)


# This class reimplements certain aspects of the event handlers, etc.
class SukajanClient(discord.Client):
    def __init__(self):
        # Load configuration file.
        try:
            self._cfg = sj_cfg.SukajanConfig()

            if self._cfg.getvalue('token') is None:
                raise Exception('Failed to retrieve token from configuration file.')
        except Exception as tmp_e:
            logging.critical(f'Failed to load configuration settings. Desc: {tmp_e}')

            os.abort()

        # Setup logging.
        try:
            setuplogging(self._cfg.getvalue('logdir'))
        except Exception as tmp_e:
            logging.critical(f'Failed to initialize logging facility. Desc: {tmp_e}')

            os.abort()

        # Let discord.py do its default initialization.
        super().__init__(intents=discord.Intents.all())
        self._gcfg = dict()

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


    # Adds guild settings to the database.
    #
    # Returns nothing.
    def __addguildsettings(self, guild: discord.Guild) -> None:
        # Convert 'created_at' time to UNIX timestamp (epoch).
        ts = math.floor(guild.created_at.timestamp())
        id = guild.id

        # Add guild info to the bots database.
        self._db.execcommand(f'INSERT INTO guilds VALUES({id}, {guild.owner_id}, {ts})')
        self._db.execcommand(f'INSERT INTO guildconfig (guildid) VALUES({id})')
        self._db.flush()

        # Add guild info to dict.
        tmp_ginfo = self._db.execquery(f'SELECT * FROM guildconfig WHERE guildid = \'{id}\'', 1)
        self._gcfg[id] = sj_cfg.SukajanGuildConfig(tmp_ginfo)


    # Removes guild settings from the database.
    #
    # Returns nothing.
    def __remguildsettings(self, guild: discord.Guild) -> None:
        # Remove guild info from the database.
        self._db.execcommand(f'DELETE FROM guilds WHERE id={guild.id}')
        self._db.execcommand(f'DELETE FROM guildconfig WHERE guildid={guild.id}')
        self._db.flush()

        # Remove guild info from dict.
        self._gcfg.pop(guild.id)


    # Updates one specific guild setting.
    #
    # Returns nothing.
    def __updguildsetting(self, guild: discord.Guild, field: str, value: any) -> None:
        # Update database setting.
        self._db.execcommand(f'UPDATE guildconfig SET {field} = \'{value}\' WHERE guildid = \'{guild.id}\'')
        self._db.flush()
        self._gcfg[guild.id].alias = value

        # Everything went well.
        logging.info(f'Successfully updated guild setting field "{field}" for guild "{guild.name}" (id: {guild.id}) to "{value}".')


    # Fetches current guild settings in case they have updated while the bot was offline.
    #
    # Returns nothing.
    def __fetchguildsettings(self, guild: discord.Guild) -> tuple[sj_cfg.SukajanGuildConfig, discord.Member]:
        # Get bot member.
        member = guild.get_member(self.user.id)

        # Get current guild settings.
        return (sj_cfg.SukajanGuildConfig((
            None,
            None,
            member.nick,
            None
        )), member)


    # Applies global settings on startup.
    #
    # Returns nothing.
    async def __applyglobalsettings(self) -> None:
        # Apply global bot account settings.
        with open(self._cfg.getvalue('avatar'), 'rb') as tmp_avatar:
            await self.user.edit(
                username=self._cfg.getvalue('alias'),
                avatar=tmp_avatar.read()
            )

        # Everything went well.
        logging.info('Successfully applied global settings.')


    # Applies guild-specific member settings when the bot goes online.
    #
    # Returns nothing.
    async def __applyguildsettings(self, guild: discord.Guild, settings: sj_cfg.SukajanGuildConfig) -> None:
        # Get bot member info and updated guild settings.
        info, member = self.__fetchguildsettings(guild)

        # Modify settings.
        # If member nick has changed, update it first.
        try:
            if settings.alias != info.alias and info.alias is not None:
                self.__updguildsetting(guild, 'alias', info.alias)

                await member.edit(nick=info.alias)
        except Exception as tmp_e:
            logging.error(f'Failed to apply guild settings for guild "{guild.name}" (id: {guild.id}). Desc: {tmp_e}')

            return

        # Everything went well.
        logging.info(f'Successfully applied settings for guild "{guild.name}" (id: {guild.id}).')


    # Reimplements the 'on_ready' event handler.
    #
    # Returns nothing.
    async def on_ready(self) -> None:
        # Apply global settings.
        try:
            await self.__applyglobalsettings()
        except Exception as tmp_e:
            logging.critical(f'Failed to apply global settings. Desc: {tmp_e}')

            os.abort()

        # Fetch guild settings for all guilds he bot is connected to.
        for tmp_guild in self.guilds:
            # Generate guild config object and put it into the dictionary.
            try:
                ginfo = self._db.execquery(f'SELECT * from guildconfig WHERE guildid = \'{tmp_guild.id}\'', 1)

                # Store guild settings in dictionary (to reduce db calls)
                self._gcfg[tmp_guild.id] = sj_cfg.SukajanGuildConfig(ginfo)

                # Apply guild settings.
                await self.__applyguildsettings(tmp_guild, self._gcfg[tmp_guild.id])
            except Exception as tmp_e:
                logging.error(f'Could not load configuration for guild {tmp_guild.name} (id: {tmp_guild.id}). Desc: {tmp_e}')

                continue

            # Everything went well for this guild.
            logging.info(f'Successfully loaded configuration for guild "{tmp_guild.name}" (id: {tmp_guild.id}).')

        # We are done setting things up and are now ready.
        logging.info(f'SukajanBot is now available as "{self.user}". Ready.')


    # Reimplements the 'on_create' event handler.
    # This handler is executed when
    #     (1) the bot creates a guild
    #     (2) the bot joins a guild
    #
    # Returns nothing.
    async def on_guild_join(self, guild: discord.Guild) -> None:
        # Add guild settings to database and flush cache.
        try:
            self.__addguildsettings(guild)
        except Exception as tmp_e:
            logging.error(f'Failed to add guild settings for guild "{guild.name}" (id: {guild.id}). Desc: {tmp_e}')

        # Print info message.
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
        try:
            self.__remguildsettings(guild)
        except Exception as tmp_e:
            logging.error(f'Failed to add guild settings for guild "{guild.name}" (id: {guild.id}). Desc: {tmp_e}')

        # Print info message.
        logging.info(f'Left guild "{guild.name}" (id: {guild.id}).')


    # Reimplements the 'on_message' event handler.
    #
    # Returns nothing.
    async def on_message(self, message: discord.Message) -> None:
        # Ignore messages sent by bots.
        if message.author.bot:
            return

        # Send a temporary 'Hello, world!' message.
        await message.channel.send('Hello, world!')


    # Reimplements the 'on_member_update' event handler.
    #
    # Returns nothing.
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        # If the bot client itself got updated, fetch the changes
        # and update database and internal cache.
        if after is after.guild.get_member(self.user.id):
            nnick = after.nick if after.nick is not None else self._cfg.getvalue('alias')
            guild = after.guild

            # Update guild settings for current guild.
            try:
                self.__updguildsetting(guild, 'alias', nnick)
            except Exception as tmp_e:
                logging.info(f'Failed to update guild setting "alias" for guild {guild.name} (id: {guild.id}). Desc: {tmp_e}')

                return

            # Everything went well.
            isdef = ' (default)' if after.nick is None else ''
            logging.info(f'Updated nickname for guild "{guild.name}" (id: {guild.id}) from "{before.nick}" to "{nnick}"{isdef}.')


