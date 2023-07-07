################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# guild.py - event handlers and commands meant for guild management

# imports
import time
import discord
import discord.ext.commands as commands
import discord.ext.tasks    as tasks

from loguru import logger

import src.module as kiyo_mod


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
        await updgentry(
            app,
            gid,
            [('left', None)]
        )

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

        INSERT INTO guildsettings (guildid) VALUES (
            {gid}
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

        # Start 'on_prune_db' loop.
        self.on_prune_db.start()

    # This event is executed when the bot joins a guild. This can happen whenever the
    # bot is invited to join the guild or the bot creates a guild.
    #
    # Returns nothing.
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        # Add basic guild data.
        conn, cur = await self._app.dbman.newconn()
        await addgentry(self._app, guild.id, conn, cur)

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
        # Get current time.
        val = int(time.time())

        # Mark guild as left.
        await updgentry(
            self._app,
            guild.id,
            [('left', val)]
        )

        # Everything went well.
        logger.info(f'Left guild \'{guild.name}\' (id: {guild.id})')


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
        othres = 20               # maximum number of ids to print

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
    #     (1) Technically, (1) can also mean a rejoin as guild settings are removed 90 days after the 'left'
    #         field for that guild had been (last) set. Thus, if the guild settings are gone, it will appear
    #         to the bot as if it joined the guild for the first time.
    clist =  [(elem, 1) for elem in glist - ilist]
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
                #     (1) Because we do not know for certain WHEN the app left the guild,
                #         we use the current time as the time of leaving.
                val = int(time.time()) if action == 2 else None
                await updgentry(
                    app,
                    gid,
                    [('left', val)],
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


