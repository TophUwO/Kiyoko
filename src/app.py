################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# app.py - main class, prepresenting application instance

# imports
import sys, math, os, traceback
import discord
import discord.app_commands as app_commands
import discord.ext.commands as commands

from loguru import logger

import src.config as kiyo_cfg
import src.db     as kiyo_db
import src.module as kiyo_mod


# This class reimplements certain aspects of the event handlers, etc.
class KiyokoApplication(commands.Bot):
    def __init__(self) -> None:
        # Setup logging.
        self.__initlogging()

        # Load global config.
        self.cfg = kiyo_cfg.KiyokoGlobalConfig('conf/.env')

        # Initialize discord.py bot client.
        super().__init__(
            command_prefix = self.cfg.getvalue('prefix'),
            help_command   = None,
            tree_cls       = app_commands.CommandTree,
            description    = None,
            intents        = discord.Intents().all()
        )
        self.gcfg = dict()

        # Establish database connection.
        self.dbman = kiyo_db.KiyokoDatabaseManager(self.cfg)

        # Initialize module manager.
        self.modman = kiyo_mod.KiyokoModuleManager(self)

        # Start the mainloop of the client.
        self.run(
            token     = str(self.cfg.getvalue('token')),
            reconnect = bool(self.cfg.getvalue('reconnect', True))
        )


    # Adds guild settings to the database.
    #
    # Returns nothing.
    async def __addguildsettings(self, guild: discord.Guild):
        # Convert 'created_at' time to UNIX timestamp (epoch).
        ts = math.floor(guild.created_at.timestamp())
        id = guild.id

        # Add guild info to the bots database.
        conn = await self.dbman.newconn()
        await self.dbman.execcommand(conn, f'INSERT INTO guilds VALUES({id}, {guild.owner_id}, 0, 0)')
        #await self.dbman.execcommand(tmp_conn, f'INSERT INTO guildsettings (guildid) VALUES({id})')
        await conn.commit()
        await conn.close()
        # Add guild info to dict.
        #tmp_ginfo = await self.dbman.execquery(tmp_conn, f'SELECT * FROM guildsettings WHERE guildid = \'{id}\'', 1)


    # Removes guild settings from the database.
    #
    # Returns nothing.
    async def __remguildsettings(self, guild: discord.Guild):
        # Remove guild info from the database.
        async with self.dbman.newconn() as tmp_conn:
            await self.dbman.execcommand(tmp_conn, f'DELETE FROM guilds WHERE id={guild.id}')
            await self.dbman.execcommand(tmp_conn, f'DELETE FROM guildsettings WHERE guildid={guild.id}')

            await tmp_conn.commit()

        # Remove guild info from dict.
        self.gcfg.pop(guild.id)


    # Updates one specific guild setting.
    #
    # Returns nothing.
    async def __updguildsetting(self, guild: discord.Guild, field: str, value: any):
        # Update database setting.
        async with self.dbman.newconn() as tmp_conn:
            await self.dbman.execcommand(tmp_conn, f'UPDATE guildsettings SET {field} = \'{value}\' WHERE guildid = \'{guild.id}\'')

            await tmp_conn.commit()

        # Update value in cache.
        self.gcfg[guild.id].alias = value

        # Everything went well.
        logger.success(f'Successfully updated guild setting field "{field}" for guild "{guild.name}" (id: {guild.id}) to "{value}".')


    # Fetches current guild settings in case they have updated while the bot was offline.
    #
    # Returns nothing.
    def __fetchguildsettings(self, guild: discord.Guild) -> tuple[kiyo_cfg.KiyokoGuildConfig, discord.Member]:
        # Get bot member.
        member = guild.get_member(self.user.id)

        # Get current guild settings.
        return (kiyo_cfg.KiyokoGuildConfig((
            None,
            None,
            member.nick,
            None,
            None
        )), member)


    # Applies global settings on startup.
    #
    # Returns nothing.
    async def __applyglobalsettings(self):
        # Apply global bot account settings.
        nname = self.cfg.getvalue('name')
        if self.user.name != nname:
            await self.user.edit(username=nname)

        # Everything went well.
        logger.success('Successfully applied global settings.')


    # Applies guild-specific member settings when the bot goes online.
    #
    # Returns nothing.
    async def __applyguildsettings(self, guild: discord.Guild, settings: kiyo_cfg.KiyokoGuildConfig) -> None:
        # Get bot member info and updated guild settings.
        info, member = self.__fetchguildsettings(guild)

        # Modify settings.
        # If member nick has changed, update it first.
        try:
            if settings.alias != info.alias and info.alias is not None:
                await self.__updguildsetting(guild, 'alias', info.alias)

                await member.edit(nick=info.alias)
        except Exception as tmp_e:
            logger.error(f'Failed to apply guild settings for guild "{guild.name}" (id: {guild.id}). Desc: {tmp_e}')

            return

        # Everything went well.
        logger.success(f'Successfully applied settings for guild "{guild.name}" (id: {guild.id}).')


    # Initializes the logging facility.
    #
    # Returns nothing.
    def __initlogging(self) -> None:
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
        await self.modman.loadmodules()
        # Sync command tree.
        await self.modman.synccmdtree()

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
                conn  = await self.dbman.newconn()
                ginfo = await self.dbman.execquery(conn, f'SELECT * from guildsettings WHERE guildid = \'{tmp_guild.id}\'', 1)
                await conn.close()
                # Store guild settings in dictionary (to reduce db calls)
                #self.gcfg[tmp_guild.id] = kiyo_cfg.KiyokoGuildConfig(ginfo)

                # Apply guild settings.
                await self.__addguildsettings(tmp_guild)
                await self.__applyguildsettings(tmp_guild, self.gcfg[tmp_guild.id])
            except Exception as tmp_e:
                logger.error(f'Could not load configuration for guild \'{tmp_guild.name}\' (id: {tmp_guild.id}). Desc: {tmp_e}')

                continue

            # Everything went well for this guild.
            logger.info(f'Successfully loaded configuration for guild \'{tmp_guild.name}\' (id: {tmp_guild.id}).')

        # We are done setting things up and are now ready.
        logger.info(f'SukajanBot is now available as \'{self.user}\'. Ready.')


    # Reimplements the 'on_create' event handler.
    # This handler is executed when
    #     (1) the bot creates a guild
    #     (2) the bot joins a guild
    #
    # Returns nothing.
    async def on_guild_join(self, guild: discord.Guild) -> None:
        # Add guild settings to database and flush cache.
        try:
            await self.__addguildsettings(guild)
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
            await self.__remguildsettings(guild)
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


    # This event handler is triggered whenever there is an exception
    # thrown inside another event handler.
    #
    # Returns nothing.
    async def on_error(self, event, *args, **kwargs) -> None:
        # Just log the error using our logger for now.
        logger.error(traceback.format_exc())


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
                await self.__updguildsetting(guild, 'alias', nnick)
            except Exception as tmp_e:
                logger.info(f'Failed to update guild setting "alias" for guild {guild.name} (id: {guild.id}). Desc: {tmp_e}')

                return

            # Everything went well.
            isdef = ' (default)' if after.nick is None else ''
            logger.info(f'Updated nickname for guild "{guild.name}" (id: {guild.id}) from "{before.nick}" to "{nnick}"{isdef}.')


