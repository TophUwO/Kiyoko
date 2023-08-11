################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# guild.py - event handlers and commands meant for guild management

# imports
import dataclasses
import time, json
import discord
import discord.ext.commands as commands
import discord.ext.tasks    as tasks

from loguru      import logger
from dataclasses import dataclass
from typing      import Optional

import src.module as kiyo_mod



# This is a special value for 'updgentry()' signifying that
# no update should be carried out. Use an UUIDv4 to at least
# most likely be unique.
# Yes, I know, this is stupid as f*ck.
SQL_NO_UPD = '0449feb0-5d19-4794-87dd7fd6d5e1e871'



# data class holding guild-related configuration
@dataclass
class KiyokoGuildConfig:
    gid:     int                                       # guild id
    logchan: Optional[tuple[bool, int]]                # [enabled, channel_id]
    mwidget: Optional[tuple[bool, int, int, int, str]] # [enabled, channel_id, lastupd, lastmcount, fmt]


# class for managing the guild config objects
class KiyokoGuildConfigManager(object):
    def __init__(self, app):
        self._dict = dict()
        self._app  = app


    # Retrieves a guild settings object from the internal dictionary.
    # If the guild id cannot be found, the function returns None.
    #
    # Returns guild settings object.
    def getgconfig(self, gid: int) -> KiyokoGuildConfig:
        return self._dict.get(gid, None)


    # Loads all guild-related configuration (i.e. 'guildsettings') into a dictionary of
    # data classes, indexed by the guild id.
    # This function can also be used to reload the config from the database in case it
    # has been updated.
    #
    # Returns nothing.
    async def loadgconfig(self) -> None:
        # Load guild configs for all guilds the client is connected to.
        conn, cur = await self._app.dbman.newconn()
        await cur.execute(f'''SELECT gs.* FROM guildsettings gs INNER JOIN guilds g ON gs.guildid = g.id WHERE g.left IS NULL''')
        qres = await cur.fetchall()
    
        # Generate guild config objects and save them in the dictionary.
        for row in qres:
            # Unpack tuple.
            (gid, config) = row

            # Parse JSON object.
            json_obj = dict(json.loads(config))
    
            # Add generated object to dict with the guild id as key.
            self._dict[gid] = KiyokoGuildConfig(
                gid,
                json_obj.get('logchan', None),
                json_obj.get('mwidget', None)
            )
    
        # Clean up.
        await cur.close()
        await conn.close()



# Updates a guild entry linked to a specified guild.
#
# Returns nothing.
async def updgentry(app, gid: int, values: list[tuple[str, any]], conn = None, cur = None) -> None:
    # Create connection and cursor object if needed.
    istmp = False
    if conn is None and cur is None:
        istmp = True

        conn, cur = await app.dbman.newconn()

    # Execute 'UPDATE'.
    for field, nval in values:
        # Do not carry out the update in case of nval == SQL_NO_UPD.
        if str(nval) == SQL_NO_UPD:
            continue

        # Allow writing NULL to a field by specifying 'NoneType' as the new value.
        # All other values are passed as strings and subsequently converted to the
        # column datatype.
        nnval = 'NULL' if nval is None else ('\'' + str(nval) + '\'')

        await cur.execute(f'UPDATE guilds SET {field} = {nnval} WHERE id = {gid}')

    # Flush db and clean up.
    if istmp:
        await cur.close()
        await conn.commit()
        await conn.close()


# Updates a guild settings entry for a given guild. If the guild entry does not exist,
# nothing will be updated.
#
# Returns nothing.
async def updgsettings(app, cfg: KiyokoGuildConfig, conn = None, cur = None) -> None:
    if cfg is None:
        return

    # Establish connection if needed.
    istmp = False
    if conn is None and cur is None:
        istmp = True

        conn, cur = await app.dbman.newconn()

    # Generate JSON document from 'cfg'.
    json_doc = json.dumps(dataclasses.asdict(cfg))
    
    # Execute 'UPDATE'.
    await cur.execute(f'UPDATE guildsettings SET config = \'{json_doc}\' WHERE guildid = {cfg.gid}')

    # Flush db and clean up.
    if istmp:
        await cur.close()
        await conn.commit()
        await conn.close()



# Adds a guild entry to the database.
#
# Returns nothing.
async def addgentry(app, gid: int, conn = None, cur = None) -> None:
    # Create connection and cursor object if needed.
    istmp = False
    if conn is None and cur is None:
        istmp = True

        conn, cur = await app.dbman.newconn()

    # If the dataset is already present, just update the 'left' field
    # because that means we rejoined.
    await cur.execute(f'SELECT id, left FROM guilds WHERE id = {gid}')
    res = await cur.fetchone()
    if res is not None:
        # Get current time (UNIX epoch).
        tnow = int(time.time())
        
        # Update database entry for the given guild.
        await updgentry(
            app,
            gid,
            [('joined', tnow), ('left', None)],
            conn,
            cur
        )

        # Flush db and clean up.
        if istmp:
            await cur.close()
            await conn.commit()
            await conn.close()

        return

    # Add the two fundamental datasets to the database.
    #     (1) basic guild info ('guilds' table)
    #     (2) guild-specific settings ('guildsettings' table)
    await cur.executescript(
        f'''
        INSERT INTO guilds VALUES (
            {gid},
            unixepoch('now'),
            NULL
        );

        INSERT INTO guildsettings (guildid, config) VALUES (
            {gid},
            '{{}}'
        )
        '''
    )

    # Flush db and clean up.
    if istmp:
        await cur.close()
        await conn.commit()
        await conn.close()


# Removes guild entries from the database.
# Note that this function also removes all data in other tables that are
# associated to the given guilds.
#
# Returns nothing.
async def remgentries(app, gids: list[int], conn = None, cur = None) -> None:
    # Create connection and cursor object if needed.
    istmp = False
    if conn is None and cur is None:
        istmp = True

        conn, cur = await app.dbman.newconn()

    # Remove any guild data.
    sres = ', '.join(map(str, gids))
    await cur.executescript(
        f'''
        DELETE FROM guilds        WHERE id      IN ({sres});
        DELETE FROM guildsettings WHERE guildid IN ({sres})
        '''
    )

    # Flush db and clean up.
    if istmp:
        await cur.close()
        await conn.commit()
        await conn.close()



# Cog defining guild-related functionality
class KiyokoModule_Guild(kiyo_mod.KiyokoModule_Base):
    # Custom initialization.
    def __init__(self, app):
        # Initialize parent class.
        super().__init__(app)

        # Start background tasks.
        self.on_prune_db.start()
        self.on_upd_mwidget.start()


    # This event is executed when the bot joins a guild. This can happen whenever the
    # bot is invited to join the guild or the bot creates a guild.
    #
    # Returns nothing.
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        # Add basic guild data.
        await addgentry(self._app, guild.id)

        # Everything went well.
        logger.info(f'Joined guild \'{guild.name}\' (id: {guild.id}).')


    # This handler is executed whenever the bot leaves a guild. That can happen when
    #    (1) the bot leaves the guild
    #    (2) the bot is kicked/banned
    #    (3) the guild owner deletes the guild
    #    (...)
    #
    # Returns nothing.
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        # Get current time (UNIX epoch).
        tnow = int(time.time())

        # Mark guild as left.
        await updgentry(
            self._app,
            guild.id,
            [('left', tnow)]
        )

        # Everything went well.
        logger.info(f'Left guild \'{guild.name}\' (id: {guild.id})')


    # Periodically checks if any member widgets need updates. If they do, we check
    # whether we can update and if yes, we issue the update command.
    #
    # Returns nothing.
    @tasks.loop(seconds = 60)
    async def on_upd_mwidget(self) -> None:
        tnow  = int(time.time()) # current time
        limit = 12 * 60 / 2      # 6 mins in seconds

        # Go through all guilds and update all member widgets that need
        # to be changed. Due to the hard rate limits we can only change a
        # channel name twice per 10 minutes. To allow for a little more room,
        # we will issue an update every 6 minutes.
        for g in self._app.guilds:
            # Get guild config.
            cfg = self._app.gcman.getgconfig(g.id)
            if cfg is None or cfg.mwidget is None:
                continue

            # Update member widget if possible.
            if cfg.mwidget[0] and cfg.mwidget[1] and tnow - cfg.mwidget[2] >= limit:
                await self.__updmwidget(cfg, g, tnow)


    # This loop checks periodically (once per week) if any of the guild infos
    # referring to guilds the bot has left are old enough (>= 90 days) to be
    # deleted.
    #
    # Returns nothing.
    @tasks.loop(hours = 24*7)
    async def on_prune_db(self) -> None:
        # Get required data.
        tnow   = int(time.time()) # current time (UNIX epoch)
        thres  = 60*60*24*90      # 90 days
        othres = 10               # maximum number of ids to print

        # Get all the entries that are too old.
        conn, cur = await self._app.dbman.newconn()
        await cur.execute(f'''SELECT id, ({tnow} - left) FROM guilds WHERE left IS NOT NULL AND ({tnow} - left) >= {thres}''')
        res  = [gid[0] for gid in await cur.fetchall()]

        # Remove all rows associated with the ids.
        if len(res) > 0:
            logger.debug(f'{len(res)} dead guild entries found: {f"> {len(res)}" if len(res) > othres else res}')
            await remgentries(self._app, res, conn, cur)

            logger.debug(f'Removed {len(res)} dead guild entries.')

        # Flush db and clean up.
        await cur.close()
        await conn.commit()
        await conn.close()


    # Updates the guild member count widget, which is modeled with an unjoinable voice
    # channel. Note that if the member count has not changed since the last update, this
    # function will do nothing.
    #
    # Returns nothing.
    async def __updmwidget(self, gcfg: KiyokoGuildConfig, guild: discord.Guild, tnow: int) -> None:
        # Do not issue update if channel member count has not changed
        # since last update.
        mcount = len(guild.members)
        if mcount == gcfg.mwidget[3]:
            return

        # Update channel name and info tuple.
        chan = guild.get_channel(gcfg.mwidget[1])
        if chan is not None:
            await chan.edit(name = gcfg.mwidget[4].format(mcount))

            logger.debug(f'Updated member count widget for guild {guild.name} (id: {guild.id}).')
        else:
            # If channel could not be found, it was probably deleted manually.
            # Unconfigure the member count widget in this case.
            logger.debug(
                f'''Automatically unconfigured member count widget for guild {guild.name} (id: {guild.id}). '''
                 '''The channel was probably manually deleted.'''
            )

        # Update widget data.
        gcfg.mwidget = (
            gcfg.mwidget[0] if chan is not None else False,
            gcfg.mwidget[1] if chan is not None else 0,
            tnow,
            mcount,
            gcfg.mwidget[4]
        )
        # Update database config in case the widget was automatically unconfigured.
        if chan is None:
           await updgsettings(self._app, gcfg)



# module entrypoint
async def setup(app) -> None:
    await app.add_cog(KiyokoModule_Guild(app))


# Synchronizes the database once the bot is ready. This may have to be done because the
# application itself can still (re-)join or leave a guild even if the bot associated with
# the app is offline. In these cases, the database of the bot becomes outdated. We perform
# this sync every time the 'on_ready' event is sent.
#
# Returns nothing.
async def syncdb(app) -> None:
    logger.debug('Synchronizing database ...')

    # Query all guilds the bot has saved in the database.
    conn, cur = await app.dbman.newconn()
    await cur.execute(f'SELECT id, left FROM guilds')

    # Generate helper lists needed for determining the action per guild.
    glist = set(guild.id for guild in app.guilds)
    qlist = [elem for elem in await cur.fetchall()]
    ilist = set(elem[0] for elem in qlist)

    # Generate a 'command list' by determining what has to be done for a particular guild.
    # The following cases can happen:
    #     (1) The guild is in app.guilds but not in the database     => app (RE-)JOINED guild while bot offline.
    #     (2) The guild is in the database but not in app.guilds     => app LEFT guild while bot offline.
    #     (3) The 'left' field is non-NULL for a guild in app.guilds => app REJOINED guild while bot offline.
    #
    # Notes:
    #     (i) Technically, (1) can also mean a rejoin as guild settings are removed 90 days after the 'left'
    #         field for that guild had been (last) set. Thus, if the guild settings are gone, it will appear
    #         to the bot as if it joined the guild for the first time.
    clist  = [(elem, 1) for elem in glist - ilist]
    clist += [(elem, 2) for elem in ilist - glist if (elem, None) in qlist]
    clist += [(elem, 3) for elem in glist & ilist if (elem, None) not in qlist]

    # Update entries in database according to the generated 'command list'.
    for gid, action in clist:
        match action:
            case 1:
                # Case (1): INSERT guild info.
                await addgentry(app, gid, conn, cur)
            case 2 | 3:
                # Case (2) or (3): UPDATE guild info.
                #
                # Notes:
                #     (i) Because we do not know for certain WHEN the app left the guild,
                #         we use the current time as the time of leaving.
                tnow = int(time.time())
                jval = tnow if action == 3 else SQL_NO_UPD
                lval = tnow if action == 2 else None
                await updgentry(
                    app,
                    gid,
                    [('joined', jval), ('left', lval)],
                    conn,
                    cur
                )

    # Flush db and clean up.
    await cur.close()
    await conn.commit()
    await conn.close()

    # Everything went well.
    if len(clist) > 0:
        logger.success('Successfully synched database.')
    else:
        logger.success('Database is up-to-date. Nothing to do.')


# Initializes or uninitializes the Member Count Widget. Guild settings are
# automatically updated.
#
# Returns nothing.
async def setupmcwidget(guild: discord.Guild, gcfg: KiyokoGuildConfig) -> None:
    mcount = len(guild.members) # initial member count
    tnow   = int(time.time())   # current UNIX timestamp.
    chanid = 0                  # channel id

    if gcfg.mwidget[0]:
        # Initialize Member Count Widget.
        chan = await guild.create_voice_channel(name = gcfg.mwidget[4].format(mcount), position = 0, user_limit = 0)
        await chan.set_permissions(guild.default_role, connect = False)

        chanid = chan.id
        logger.info(f'Configured mcwidget for guild \'{guild.name}\' (id: {guild.id}). Channel id: {chan.id}.')
    else:
        if gcfg.mwidget[1] == 0:
            return

        # Delete channel.
        await guild.get_channel(gcfg.mwidget[1]).delete()
        
        logger.info(f'Deleted mcwidget channel for guild \'{guild.name}\' (id: {guild.id}).')

    # Update mwidget data.
    gcfg.mwidget = (
        gcfg.mwidget[0],
        chanid,
        tnow,
        mcount,
        gcfg.mwidget[4]
    )


