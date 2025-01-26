################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023-25 TophUwO All rights reserved.                     #
################################################################

# strike.py - strike system for use by server moderation

# imports
import time
import datetime
import random
import discord
import re
import json
import jsonschema

import discord.ext.tasks as tasks

from loguru               import logger
from typing               import Optional
from discord.app_commands import *
from datetime             import timedelta

import src.utils as kiyo_utils
import src.error as kiyo_error



@discord.app_commands.guild_only()
class KiyokoCommandGroup_Strike(discord.app_commands.Group):
    def __init__(self, app, name: str, desc: str):
        super().__init__(name = name, description = desc)
    
        self._app = app
        self.add_command(self.subg_config)

        self.__on_delexpired.start()


    # Defines the placeholder 'config' group.
    #
    # Returns itself.
    @property
    def subg_config(self) -> discord.app_commands.Group:
        subg_config = discord.app_commands.Group(
            name        = 'config',
            description = 'manages the thresholds for the strike system for the current guild'
        )

        # Defines the function that manages the thresholds for the strike system.
        #
        # Returns nothing.
        @subg_config.command(name = 'submit', description = 'submits the config as a JSON document, updating it immediately')
        @discord.app_commands.describe(config = 'file that contains the new config; must be valid JSON')
        @discord.app_commands.check(kiyo_utils.isenabled)
        @discord.app_commands.check(kiyo_utils.updcmdstats)
        @discord.app_commands.checks.has_permissions(administrator = True)
        async def cmd_submit(inter: discord.Interaction, config: discord.Attachment) -> None:
            # We must enter a file.
            if config is None or config.content_type.find("application/json") == -1:
                raise kiyo_error.AppCmd_InvalidParameter

            # Parse the file as JSON.
            cfg = json.loads(await config.read())
            if cfg is not None:
                with open('res/strikesys_schema.json', 'r') as schema:
                    jsonschema.validate(instance = cfg, schema = json.load(schema))

            # Open connection.
            dbconn, cur = await self._app.dbman.newconn()
            # Delete the old config.
            await cur.execute(f'DELETE FROM strike_cfg WHERE guildid = {inter.guild_id} AND (key = \'decay\' OR key = \'threshold\')')

            # Update the data.
            await cur.execute(
                f'''
                INSERT INTO strike_cfg
                VALUES({inter.guild_id}, \'decay\', \'{self.__iso8601tosec(cfg['decay'])}\', NULL)
                '''
            );
            for thres in cfg['thresholds']:
                # Format p2 if necessary.
                p2 = thres['action']
                if thres['extra'] is not None:
                    p2 += f''' {self.__iso8601tosec(thres['extra'])}'''

                # Insert threshold entry into db.
                await cur.execute(
                    f'''
                    INSERT INTO strike_cfg
                    VALUES({inter.guild_id}, \'threshold\', \'{thres['pt']}\', \'{p2}\')
                    '''
                )

            # Send feedback to caller.
            embed, file = kiyo_utils.cfgupdembed(
                inter = inter,
                desc  = 'strikesys',
                upd   = []
            )
            await kiyo_utils.sendmsgsecure(inter, embed = embed, file = file)

            # Close connection.
            await dbconn.commit()
            await cur.close()
            await dbconn.close()

        # Formats the guild config for the strike system and returns it as a JSON document.
        #
        # Returns nothing.
        @subg_config.command(
            name        = 'query',
            description = 'queries the current strike system configuration as a JSON document'
        )
        @discord.app_commands.check(kiyo_utils.isenabled)
        @discord.app_commands.check(kiyo_utils.updcmdstats)
        @discord.app_commands.checks.has_permissions(administrator = True)
        async def cmd_query(inter: discord.Interaction) -> None:
            raise kiyo_error.AppCmd_NotImplemented

        return subg_config


    # Adds a strike to a given user in the current guild, including a reason for the
    # strike and a rating.
    #
    # Returns nothing.
    @discord.app_commands.command(name = 'add', description = 'adds a new strike to a member')
    @discord.app_commands.describe(
        uid    = 'member that is to be striked',
        pt     = 'how many points are to be added for the infraction this strike is issued for; must be > 0',
        reason = 'textual description of why the strike was issued; must not be empty',
        msgref = '(optional) reference to the message for additional proof',
        silent = '(optional) controls whether or not the user is notified of the strike, useful when migrating from a previous system; defaults to \'False\''
    )
    @discord.app_commands.guild_only()
    @discord.app_commands.check(kiyo_utils.isenabled)
    @discord.app_commands.check(kiyo_utils.updcmdstats)
    @discord.app_commands.checks.has_permissions(moderate_members = True)
    @discord.app_commands.checks.bot_has_permissions(moderate_members = True, kick_members = True, ban_members = True)
    async def cmd_add(self, inter: discord.Interaction, uid: discord.Member, pt: int, reason: str, msgref: Optional[str], silent: Optional[bool] = False) -> None:
        ts = int(time.time())
        # pt must be > 0 and reason must be non-empty.
        if pt < 1 or reason is None or len(reason) == 0:
            raise kiyo_error.AppCmd_InvalidParameter

        # Add the strike to the user. Do this for as long as the UNIQUE constraint fails.
        # This can only happen if there already exists a strike with the same ID. This
        # should almost never happen.
        dbconn, cur = await self._app.dbman.newconn()
        sid = ''
        while 1:
            sid = self.__genstrid()

            try:
                await cur.execute(
                    f'''
                    INSERT INTO strike_entr
                    VALUES(
                        {inter.guild_id},
                        {uid.id},
                        {inter.user.id},
                        \'{sid}\',
                        \'{reason}\',
                        {pt},
                        {ts},
                        \'{'NULL' if msgref is None else msgref}\'
                    )
                    '''
                )
            except: continue

            break
        await dbconn.commit()

        # Retrieve what action is to be taken now that the new points have been calculated.
        await cur.execute(
            f'''
            WITH s AS (
                SELECT SUM(pt) AS total_sum
                FROM strike_entr
                WHERE guildid = {inter.guild_id}
                    AND uid = {uid.id}
                GROUP BY uid
            ) SELECT p2, s.total_sum
              FROM strike_cfg
              INNER JOIN s ON 1 = 1
              WHERE guildid = {inter.guild_id} AND key = 'threshold' AND s.total_sum >= CAST(p1 AS INT)
              ORDER BY CAST(p1 AS INT) DESC
              LIMIT 1;
            '''
        )
        res = await cur.fetchone()

        # Now that we know what to do, do it.
        if res is not None:
            # Fetch the user so we can message them if the action necessitates it.
            user = await inter.client.fetch_user(uid.id)
            rstr = reason + (f' ({msgref})' if msgref is not None else '')

            # Fix grammar of warn embed.
            gr = {
                'warn':    'warned on',
                'timeout': 'timeout on',
                'kick':    'kicked from',
                'ban':     'banned from'
            };

            # If there is something to do, we parse the action string. This string contains 
            # of one word and optionally a number.
            command = str(res[0]).split(' ')
            # Firstly, notify the recipient. Only do this if desired.
            if not silent:
                (embed, file) = self.__makewarnembed(gr[command[0]], inter.guild, reason, int(res[1]), msgref)

                await user.send(embed = embed, file = file)

            # Finally, carry out the action.
            if command[0] == 'timeout':
                # Timeout the user.
                try:
                    await uid.timeout(timedelta(seconds = int(command[1])))
                except discord.Forbidden:
                    raise kiyo_error.AppCmd_MissingPermissions
            elif command[0] == 'kick':
                # Check if the caller can kick members.
                if not inter.user.resolved_permissions.kick_members:
                    raise kiyo_error.AppCmd_MissingPermissions

                # Kick the member from the server. Do not delete strikes.
                try:
                    await uid.kick(reason = rstr)
                except discord.Forbidden:
                    raise kiyo_error.AppCmd_MissingPermissions
            elif command[0] == 'ban':
                # Check if the caller can ban members.
                if not inter.user.resolved_permissions.ban_members:
                    raise kiyo_error.AppCmd_MissingPermissions

                # At last, if this damn person cannot keep it together, we ban them.
                try:
                    await uid.ban(reason = rstr)
                except discord.Forbidden:
                    raise kiyo_error.AppCmd_MissingPermissions

            # Send feedback to caller.
            embed, file = self.__makefeedbackembed(inter.user, uid, sid, reason, pt, res[0], msgref)
            await kiyo_utils.sendmsgsecure(inter, embed = embed, file = file)

        # Clean up the mess.
        await cur.close()
        await dbconn.close()


    # Removes a strike for a given member based on its ID.
    #
    # Returns nothing.
    @discord.app_commands.command(name = 'delete', description = 'deletes a strike by its ID for the given user')
    @discord.app_commands.describe(
        uid = 'ID of the user whose strike identified by \'sid\' is to be deleted',
        sid = 'ID of the strike that is to be deleted'
    )
    @discord.app_commands.guild_only()
    @discord.app_commands.check(kiyo_utils.isenabled)
    @discord.app_commands.check(kiyo_utils.updcmdstats)
    @discord.app_commands.checks.has_permissions(moderate_members = True)
    @discord.app_commands.checks.bot_has_permissions(moderate_members = True, kick_members = True, ban_members = True)
    async def cmd_delete(self, inter: discord.Interaction, uid: str, sid: str) -> None:
        iuid = 0
        try:
            iuid = int(uid)
        except:
            raise kiyo_error.AppCmd_InvalidParameter

        # Delete the strike.
        dbconn, cur = await self._app.dbman.newconn()
        await cur.execute(
            f'''
            DELETE FROM strike_entr
            WHERE guildid = {inter.guild_id}
                AND uid = {iuid}
                AND id = \'{sid}\'
            '''
        )
        await dbconn.commit()
        await cur.close()
        await dbconn.close()

        # Format response.
        wasdel = cur.rowcount > 0
        file = discord.File(self._app.resman.getresource('success').url, filename = 'success.png')
        e = discord.Embed(
            color       = 0x2ecc71,
            title       = f'Strike management for user with ID ``{iuid}``',
            description =
                f'Deleted strike with ID ``{sid}`` for user with ID ``{iuid}``. Note that strikes cannot be restored.'
                if wasdel else
                f'No strike was deleted. It is likely that the ID ``{sid}`` does not identify a strike for the user with ID ``{iuid}``.',
            timestamp   = datetime.datetime.now()
        )
        e.set_author(name = inter.user.display_name, icon_url = inter.user.display_avatar.url)
        e.set_thumbnail(url = 'attachment://success.png')

        # Send response.
        await inter.response.send_message(embed = e, file = file)


    # Clears all strikes for the user identified by the given ID in the scope of the current guild.
    #
    # Returns nothing.
    @discord.app_commands.command(name = 'clear', description = 'deletes all strikes for the user identified by the given ID')
    @discord.app_commands.describe(uid = 'ID that identifies the user for whom all strikes are to be deleted')
    @discord.app_commands.guild_only()
    @discord.app_commands.check(kiyo_utils.isenabled)
    @discord.app_commands.check(kiyo_utils.updcmdstats)
    @discord.app_commands.checks.has_permissions(moderate_members = True)
    @discord.app_commands.checks.bot_has_permissions(moderate_members = True, kick_members = True, ban_members = True)
    async def cmd_clear(self, inter: discord.Interaction, uid: str) -> None:
        iuid = 0
        try:
            iuid = int(uid)
        except:
            raise kiyo_error.AppCmd_InvalidParameter

        # Delete the strikes.
        dbconn, cur = await self._app.dbman.newconn()
        await cur.execute(f'DELETE FROM strike_entr WHERE guildid = {inter.guild_id} AND uid = {iuid}')
        await dbconn.commit()
        await cur.close()
        await dbconn.close()

        # Format response message.
        file = discord.File(self._app.resman.getresource('success').url, filename = 'success.png')
        e = discord.Embed(
            color       = 0x2ecc71,
            title       = f'Strike management for user with ID ``{iuid}``',
            description =
                f'Cleared all (``{cur.rowcount}``) strikes for user with ID ``{iuid}``. Note that strikes cannot be restored.'
                if cur.rowcount > 0 else
                f'*No strikes to clear for user with ID ``{iuid}`` could be found.**',
            timestamp   = datetime.datetime.now()
        )
        e.set_author(name = inter.user.display_name, icon_url = inter.user.display_avatar.url)
        e.set_thumbnail(url = 'attachment://success.png')

        # Send the message.
        await inter.response.send_message(embed = e, file = file)


    # Lists all strikes for a given user or the current user in the scope of the current guild.
    #
    # Returns nothing.
    @discord.app_commands.command(name = 'list', description = 'lists all strikes for either the current or a given member')
    @discord.app_commands.describe(uid = '(optional) ID identifying the user whose strikes are to be listed; defaults to the caller')
    @discord.app_commands.guild_only()
    @discord.app_commands.check(kiyo_utils.isenabled)
    @discord.app_commands.check(kiyo_utils.updcmdstats)
    @discord.app_commands.checks.bot_has_permissions(moderate_members = True, kick_members = True, ban_members = True)
    async def cmd_list(self, inter: discord.Interaction, uid: Optional[str]) -> None:
        iuid = 0
        try:
            iuid = int(uid)
        except:
            raise kiyo_error.AppCmd_InvalidParameter

        # If member is not None and not the caller, then the user must have elevated privileges.
        if iuid is not None and iuid != inter.user.id:
            reqperm = discord.Permissions(moderate_members = True)

            if inter.permissions < reqperm:
                raise kiyo_error.AppCmd_MissingPermissions
        # If member is None, default to caller.
        if iuid is None:
            iuid = inter.user.id
        elevated = discord.Permissions(moderate_members = True) <= inter.user.resolved_permissions

        # Query all strikes the member has accumulated.
        dbconn, cur = await self._app.dbman.newconn()
        await cur.execute(f'SELECT * FROM strike_entr WHERE guildid = {inter.guild_id} AND uid = {iuid} ORDER BY ts ASC')
        strikes = await cur.fetchall()
        await cur.close()
        await dbconn.close()

        # Format the embed body.
        body = f'The following are all strikes for the user with ID ``{iuid}``:\n\n'
        for entry in strikes:
            s = inter.client.get_user(int(entry[2]))
            body += f'**Strike** (ID: ``{entry[3]}``) - ``{int(entry[5])}`` points\n'

            body += f'- **Date**: {datetime.datetime.fromtimestamp(float(entry[6])).strftime("%A %d, %Y - %r")}\n'
            if elevated:
                body += f'- **Issuer**: ``{s.display_name if s is not None else "n/a"}`` (ID: ``{s.id}``)\n'
            body += f'- **Reason**: {entry[4]}\n'
            if entry[7] is not None and entry[7] != 'NULL':
                body += f'- **Context**: [Jump to message.](<{entry[7]}>)\n'
        if len(strikes) == 0:
            body += '*No strikes could be found for this user.*'

        # Format the feedback embed.
        file = discord.File(self._app.resman.getresource('info').url, filename = 'info.png')
        e = discord.Embed(
            color       = 0x3498dB,
            title       = f'Strikes for user with ID ``{iuid}``',
            description = body,
            timestamp   = datetime.datetime.now()
        )
        e.set_author(name = inter.user.display_name, icon_url = inter.user.display_avatar.url)
        e.set_thumbnail(url = 'attachment://info.png')

        # Send the message.
        await inter.response.send_message(embed = e, file = file)


    # Converts simple ISO 8601 notation into seconds.
    #
    # Returns duration in seconds.
    def __iso8601tosec(self, input: str) -> int:
        # Define a table that will be used to calculate the total number of
        # seconds to mute the member for.
        lut = {
            'h': 60 * 60 * 1,
            'd': 24 * 60 * 60 * 1,
            'w': 7 * 24 * 60 * 60 * 1,
            'm': 4 * 7 * 24 * 60 * 60 * 1,
            'y': 12 * 4 * 7 * 24 * 60 * 60 * 1
        }
        # Now, we are muting a user. For that, we need to specify a mute duration.
        dur = re.findall(r'(\d+[ymwdh])+', input)
        sdur = 0
        for val, unit in dur:
            sdur += lut[unit] * int(val)

        return sdur


    # Prepares the embed that will be used to send to the user in order to inform them about
    # their infraction.
    #
    # Returns embed object, ready to be sent.
    def __makewarnembed(self, a: str, g: discord.Guild, reason: str, ptc: int, msgref: Optional[str]) -> tuple[discord.Embed, discord.File]:
        file = discord.File(self._app.resman.getresource('strike').url, filename = 'strike.png')

        e = discord.Embed(
            color = 0xf1c40f,
            title = f'You have been {a} ``{g.name}``',
            description = 
                  f'For a recent infraction, you have been {a} ``{g.name}``. For more information and context, refer to'
                + ' the fields below or contact the staff team. '
                + (f'Please note that future infractions may result in more stringent sanctions. ' if a != 'banned from' else '')
                + f'Your current point count is ``{ptc}``.'
                + '\n\n'
                + f'In order to see your current strikes and more, use ``/strike list``. Note that this may not be '
                + 'possible when you are currently timed-out.',
            timestamp = datetime.datetime.now()
        )
        e.add_field(name = 'Reason', value = reason)
        if msgref is not None:
            e.add_field(name = 'Context', value = f'[Jump to message.](<{msgref}>)')
        e.set_footer(text = g.name, icon_url = g.icon)
        e.set_thumbnail(url = "attachment://strike.png")

        return (e, file)


    # Prepares the strike add feedback message. This will be sent to the moderator that used
    # the strike command via a non-ephemeral message.
    #
    # Returns nothing.
    def __makefeedbackembed(self, s: discord.Member, u: discord.Member, id: str, reason: str, pt: int, c: str, msgref: Optional[str]) -> tuple[discord.Embed, discord.File]:
        file = discord.File(self._app.resman.getresource('success').url, filename = 'success.png')

        e = discord.Embed(
            color       = 0x2ecc71,
            title       = f'Strike added for ``{u.display_name}``',
            description = f'A new strike (ID: ``{id}``) has been added to member <@{u.id}>. The recipient has been notified. Detailed information can be found below:',
            timestamp   = datetime.datetime.now()
        )
        e.add_field(name = 'Member', value = f'<@{u.id}>')
        e.add_field(name = 'Points', value = f'``{pt}``')
        e.add_field(name = 'Reason', value = reason)
        e.add_field(name = 'Action Taken', value = c)
        if msgref is not None:
            e.add_field(name = 'Context', value = f'[Jump to message.](<{msgref}>)')
        e.set_thumbnail(url = 'attachment://success.png')
        e.set_author(name = s.display_name, icon_url = s.display_avatar.url)

        return (e, file)


    # Generates a random strike ID.
    #
    # Returns strike ID as string.
    def __genstrid(self) -> str:
        return ''.join(random.choices('0123456789abcdef', k = 4))


    # Periodically deletes strikes that have expired since the last time they were checked.
    #
    # Returns nothing.
    @tasks.loop(hours = 24)
    async def __on_delexpired(self) -> None:
        tnow = int(time.time())

        # Go through all guilds and delete all expired strikes.
        dbconn, cur = await self._app.dbman.newconn()
        for guild in self._app.guilds:
            # Delete all strikes that have expired according to the current decay and guild.
            await cur.execute(
                f'''
                WITH d AS (
                    SELECT p1 FROM strike_cfg
                    WHERE guildid = {guild.id} AND key = \'decay\'
                    LIMIT 1
                )
                DELETE FROM strike_entr
                WHERE guildid = {guild.id} AND ts + CAST((SELECT p1 FROM d) AS INT) <= {tnow}
                '''
            )

        # Clean up.
        await dbconn.commit()
        await cur.close()
        await dbconn.close()


        

# module entrypoint
async def setup(app) -> None:
     # Initialize 'strike' module.
    cmdgroup = None
    try:
        cmdgroup = KiyokoCommandGroup_Strike(
            app,
            name = 'strike',
            desc = 'controls the integrated per-guild strike system'
        )
    except Exception as tmp_e:
        logger.error(f'Failed to initialize \'strike\' module. Reason: {tmp_e}')

        return

    # If everything went well, add the command to the tree.
    app.tree.add_command(cmdgroup)

    
