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
import discord
import discord.ext.commands as commands
import os
import math
import sys
from loguru import logger

import src.config as sj_cfg
import src.db as sj_db


# This class reimplements certain aspects of the event handlers, etc.
class SukajanClient(commands.Bot):
    def __init__(self) -> None:
        # Setup logging.
        self.__initlogging()

        # Load configuration file.
        self.cfg = sj_cfg.SukajanConfig('conf/.env')

        # Let discord.py do its default initialization.
        super().__init__(
            command_prefix=self.cfg.getvalue('prefix', '/'),
            intents=discord.Intents.all(),
            help_command=None
        )
        self.gcfg = dict()

        # Establish database connection.
        self._db = sj_db.SukajanDatabase(self.cfg)

        # Start the mainloop of the client.
        self.run(
            token=self.cfg.getvalue('token'),
            reconnect=bool(self.cfg.getvalue('reconnect', True))
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
        self._db.execcommand(f'INSERT INTO guildsettings (guildid) VALUES({id})')
        self._db.flush()

        # Add guild info to dict.
        tmp_ginfo = self._db.execquery(f'SELECT * FROM guildsettings WHERE guildid = \'{id}\'', 1)
        self.gcfg[id] = sj_cfg.SukajanGuildConfig(tmp_ginfo)


    # Removes guild settings from the database.
    #
    # Returns nothing.
    def __remguildsettings(self, guild: discord.Guild) -> None:
        # Remove guild info from the database.
        self._db.execcommand(f'DELETE FROM guilds WHERE id={guild.id}')
        self._db.execcommand(f'DELETE FROM guildsettings WHERE guildid={guild.id}')
        self._db.flush()

        # Remove guild info from dict.
        self.gcfg.pop(guild.id)


    # Updates one specific guild setting.
    #
    # Returns nothing.
    def __updguildsetting(self, guild: discord.Guild, field: str, value: any) -> None:
        # Update database setting.
        self._db.execcommand(f'UPDATE guildsettings SET {field} = \'{value}\' WHERE guildid = \'{guild.id}\'')
        self._db.flush()
        self.gcfg[guild.id].alias = value

        # Everything went well.
        logger.success(f'Successfully updated guild setting field "{field}" for guild "{guild.name}" (id: {guild.id}) to "{value}".')


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
            None,
            None
        )), member)


    # Applies global settings on startup.
    #
    # Returns nothing.
    async def __applyglobalsettings(self) -> None:
        # Apply global bot account settings.
        await self.user.edit(username=self.cfg.getvalue('name'))

        # Everything went well.
        logger.success('Successfully applied global settings.')


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
            logger.error(f'Failed to apply guild settings for guild "{guild.name}" (id: {guild.id}). Desc: {tmp_e}')

            return

        # Everything went well.
        logger.success(f'Successfully applied settings for guild "{guild.name}" (id: {guild.id}).')


    # Loads all extentions present.
    #
    # Returns nothing.
    async def __loadextentions(self) -> None:
        # Inject modules. Only attempt to load them if the path
        # exists.
        modpath = self.cfg.getvalue('moduledir')
        if os.path.exists(modpath):
            nextentions = 0

            for fname in os.listdir(modpath):
                if fname.endswith('.py'):
                    modname = fname[:-3]
                    try:
                        await self.load_extension('src.modules.' + modname)
                    except Exception as tmp_e:
                        logger.error(f'Failed to load module "{modname}". Reason: {tmp_e}')

                        continue

                    logger.success(f'Successfully loaded module "{modname}".')
                    nextentions += 1
            logger.debug(f'Loaded {nextentions} modules.')
        else:
            logger.debug('No modules to load.')


    # Syncs the command tree with all guilds the bot is connected
    # to.
    #
    # Returns nothing.
    async def __synccmdtree(self) -> None:
        iserr = False
        for guild in self.guilds:
            try:
                await self.tree.sync(guild=guild)
            except Exception as tmp_e:
                logger.error(f'Failed to sync command tree to guild "{guild.name}" (id: {guild.id}). Desc: {tmp_e}')

                iserr = True
                continue

        # Everything went well.
        if not iserr:
            logger.success('Successfully synced command tree to discord.')


    # Initializes the logging facility.
    #
    # Returns nothing.
    def __initlogging(self) -> None:
        # Get required settings.
        logdir = 'logs'
        fname  = 'log_{time:MM-DD-YYYY_HHmmss}.log'
        fmt    = '[{time:MM-DD-YYYY HH:mm:ss}] <lvl>{level:<8}</> {module}: {message}'
        rot    = '00:00'
        ret    = '14 days'

        # Create 'log' directory if it does not exist.
        try:
            if not os.path.exists(logdir):
                os.mkdir(logdir)
        except:
            logger.critical(f'Failed to create log directory \'{logdir}\'.')

            raise
      
        # Setup loguru.
        logger.remove()
        logger.level('WARNING', color='<yellow>')
        logger.add(sys.stderr, format=fmt, colorize=True)
        logger.add(logdir + '/' + fname, format=fmt, rotation=rot, retention=ret)

        # Everything went well.
        logger.success('Successfully initialized logging facility.')


    # Reimplements the 'on_ready' event handler.
    #
    # Returns nothing.
    async def on_ready(self) -> None:
        # Load extentions.
        await self.__loadextentions()
        # Sync command tree.
        await self.__synccmdtree()

        # Apply global settings.
        try:
            await self.__applyglobalsettings()
        except:
            logger.error(f'Failed to apply global settings.')

            raise

        # Fetch guild settings for all guilds he bot is connected to.
        for tmp_guild in self.guilds:
            # Generate guild config object and put it into the dictionary.
            try:
                ginfo = self._db.execquery(f'SELECT * from guildsettings WHERE guildid = \'{tmp_guild.id}\'', 1)

                # Store guild settings in dictionary (to reduce db calls)
                self.gcfg[tmp_guild.id] = sj_cfg.SukajanGuildConfig(ginfo)

                # Apply guild settings.
                await self.__applyguildsettings(tmp_guild, self.gcfg[tmp_guild.id])
            except Exception as tmp_e:
                logger.error(f'Could not load configuration for guild {tmp_guild.name} (id: {tmp_guild.id}). Desc: {tmp_e}')

                continue

            # Everything went well for this guild.
            logger.info(f'Successfully loaded configuration for guild "{tmp_guild.name}" (id: {tmp_guild.id}).')

        # We are done setting things up and are now ready.
        logger.info(f'SukajanBot is now available as "{self.user}". Ready.')


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
            logger.error(f'Failed to add guild settings for guild "{guild.name}" (id: {guild.id}). Desc: {tmp_e}')

        # Print info message.
        msg = 'Created and joined' if guild.owner_id == self.user.id else 'Joined'
        logger.info(f'{msg} guild "{guild.name}" (id: {guild.id}).')


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
            logger.error(f'Failed to add guild settings for guild "{guild.name}" (id: {guild.id}). Desc: {tmp_e}')

        # Print info message.
        logger.info(f'Left guild "{guild.name}" (id: {guild.id}).')


    # Reimplements the 'on_message' event handler.
    #
    # Returns nothing.
    async def on_message(self, message: discord.Message) -> None:
        # Ignore messages sent by bots.
        if message.author.bot:
            return


    # Reimplements the 'on_member_update' event handler.
    #
    # Returns nothing.
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        # If the bot client itself got updated, fetch the changes
        # and update database and internal cache.
        if after is after.guild.get_member(self.user.id):
            nnick = after.nick if after.nick is not None else self.cfg.getvalue('alias')
            guild = after.guild

            # Update guild settings for current guild.
            try:
                self.__updguildsetting(guild, 'alias', nnick)
            except Exception as tmp_e:
                logger.info(f'Failed to update guild setting "alias" for guild {guild.name} (id: {guild.id}). Desc: {tmp_e}')

                return

            # Everything went well.
            isdef = ' (default)' if after.nick is None else ''
            logger.info(f'Updated nickname for guild "{guild.name}" (id: {guild.id}) from "{before.nick}" to "{nnick}"{isdef}.')


