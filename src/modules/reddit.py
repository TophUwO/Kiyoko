################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# reddit.py - stream reddit submissions from your community subreddit
#             to your discord server

# imports
import discord, asyncio
import asyncpraw, typing
import datetime, time, enum
import configparser

from loguru       import logger
from urllib.parse import urlparse
from typing       import Optional

import discord.ext.tasks as tasks

import src.utils         as kiyo_utils
import src.error         as kiyo_error
import src.modules.guild as kiyo_guild



# exception for not configured 'redinitpath' field in .env
class KiyokoRedditInitpathError(Exception):
    def __init__(self):
        super().__init__('\'{redinitpath}\' not could not be found in \'.env\'.')

# exception for missing or malformed reddit initialization file
class KiyokoRedditConfigFileError(Exception):
    def __init__(self, file: str):
        super().__init__(f'Reddit initialization file \'{file}\' could not be found or is malformed.')

# exception for not properly configured reddit initialization file
class KiyokoRedditConfigError(Exception):
    def __init__(self, file: str):
        super().__init__(f'Reddit initialization file \'{file}\' is not properly configured. (missing/empty fields?).')


# enum describing subreddit status (i.e. available, nonexistent, blacklisted)
class KiyokoSubredditStatus(enum.Enum):
    AVAILABLE   = 0, # sub is available, i.e. can be listened to
    NONEXISTENT = 1, # sub does not exist
    BLACKLISTED = 2, # sub exists but is globally blacklisted
    ALRINFEED   = 3  # sub is already being listened to by the current guild



# class holding all sub-reddits the bot listens to globally
class KiyokoSubredditManager:
    MTLEN = 50  # max. number of chars of a post embed title preview
    MBLEN = 256 # max. number of chars of a post body preview

    def __init__(self, app):
        self._app             = app    # application instance
        self._cfg             = dict() # read-only reddit config
        self._blist: set[str] = set()  # global blacklist
        self._feed: set[str]  = set()  # current feed
        self._lid: str        = ''     # id of last submission processed
        self._lts: int        = 0      # timestamp of the latest processed submission
        self._subl            = None   # subreddit listener
        self._lfupd           = 0      # last feed creation timestamp

        # Read '.reddit' init file.
        path = self._app.cfg.getvalue('global', 'redinitpath')
        if path is not None:
            config = configparser.ConfigParser()

            # Parse config file.
            try:
                config.read(path)
                self._cfg = config['global']

                # Check if all keys are present and configured.
                reqkeys = ['client_id', 'client_secret', 'user_agent', 'username', 'password']
                for key in reqkeys:
                    if not config.has_option('global', key) or self._cfg[key] in [None, '']:
                        raise KiyokoRedditConfigError(path)

                logger.debug(f'Successfully read \'{path}\' config file.')
            except:
                raise KiyokoRedditConfigFileError(path)

            # Initialize blacklist if there is any.
            if config.has_option('global', 'blacklist') and self._cfg['blacklist'] not in [None, '']:
                self._blist = set(self._cfg['blacklist'].strip().replace(' ', '').split(','))
        else:
            raise KiyokoRedditInitpathError

        # Init reddit instance.
        self._reddit = asyncpraw.Reddit(
            client_id     = self._cfg['client_id'],
            client_secret = self._cfg['client_secret'],
            username      = self._cfg['username'],
            password      = self._cfg['password'],
            user_agent    = self._cfg['user_agent']
        )

        # Init data-structure.
        # key:   str                   => name
        # value: list[tuple[int, int]] => [gid, cid, prole]
        self._data: dict[str, list[tuple[int, int, int]]] = dict()

        # Start the stream.
        self.__on_scrape_newsubms.start()


    # Uninitialize the 'reddit' instance.
    def __del__(self):
        asyncio.get_event_loop().run_in_executor(self._reddit.close())


    # Initializes the data-structure. This has to be done after the module
    # has been loaded because of the fact that guild configs get loaded after
    # modules.
    #
    # Returns nothing.
    def initdata(self) -> None:
        # Go through all guild configs and populate the data-structure.
        for gcfg in self._app.gcman.guildconfigs():
            # Get guild-specific reddit config.
            if gcfg.reddit is None:
                continue

            # Populate data-structure.
            for entry in gcfg.reddit:
                try:
                    # Add sub to feed.
                    self._feed.add(entry.get('id'))

                    # Add subreddit to data storage.
                    self.addsubreddit(entry.get('id'), gcfg.gid, entry.get('broadcast'), entry.get('prole', 0))
                except KeyError:
                    logger.error(f'Subreddit listener entry malformed: {entry}')


    # Adds a subreddit to the internal data storage. If it already exists,
    # nothing will be done.
    #
    # Returns nothing.
    def addsubreddit(self, subn: str, gid: int, cid: int, prole: int = 0) -> None:
         self._data[subn] = self._data.get(subn, None) or list()
         self._data[subn].append((gid, cid, prole))


    # Removes a subreddit listener from the internal data storage.
    # If the guild is not subbed to the given subreddit, this function
    # does nothing.
    #
    # Returns True if the listener was removed, False if not.
    def remsubreddit(self, subn: str, gid: int) -> bool:
        sublist = self._data.get(subn, [])
        try:
            sublist.remove([(id, cid, prole) for (id, cid, prole) in sublist if id == gid][0])
        except ValueError:
            return False

        return True


    # Queries the subreddit status for the given guild and subreddit.
    #
    # Returns a 2-tuple, describing the subreddit's status. The values
    # signify the following in this order:
    #  (1) sub name
    #  (2) sub status
    async def querysubstatus(self, gid: int, sub: str) -> tuple[str, KiyokoSubredditStatus]:
        res = KiyokoSubredditStatus.AVAILABLE

        # Check if the guild is already listening to the sub.
        if self.__isguildsubbed(gid, sub):
            res = KiyokoSubredditStatus.ALRINFEED
        # Check if the sub is blacklisted.
        elif sub in self._blist:
            res = KiyokoSubredditStatus.BLACKLISTED

        # Return final result.
        return (sub, res)


    # Updates the feed of the subreddit stream. This happens whenever a guild adds
    # a previously non-tracked subreddit to the manager.
    #
    # Returns nothing.
    async def updfeed(self, upd: tuple[str, bool]) -> None:
        # Add or remove the given sub.
        (sname, isadd) = upd

        # If given sub is blacklisted, do not attempt to add. Attempting to remove it is also nonsensical because
        # they cannot be added in the first place.
        try:
            if isadd and sname not in self._blist:
                self._feed.add(sname)
                # If no guilds are listening to the subreddit any longer, remove the entry
                # completely.
            elif not isadd and self.__nsubs(sname) == 0:
                self._feed.remove(sname)
        except KeyError:
            # If the sub entry does not exist, 'remove' will throw a KeyError. Because it's not really important,
            # we just catch and ignore the exception.
            pass

        # Rebuild feed.
        await self.__buildfeed()


    # Checks whether the guild is currently subscribed to the given subreddit.
    #
    # Returns True if the guild is subscribed to the given sub,
    # False if not.
    def __isguildsubbed(self, gid: int, name: str) -> bool:
        for (guildid, _, _) in self._data.get(name) or []:
            if gid == guildid:
                return True

        return False


    # Rebuilds the feed using the current list of subs that are listened to.
    #
    # Returns nothing.
    async def __buildfeed(self) -> None:
        try:
            self._subl  = await self._reddit.subreddit('+'.join(self._feed))
            self._lfupd = int(time.time())

            logger.info(f'Successfully updated feed to {self._feed} (time: {self._lfupd})')
        except Exception as tmp_e:
            logger.error(f'Could not update feed. Reason: {tmp_e}')


    # This function formats the embed that will be sent to all subscribers of a given subreddit that has just
    # been submitted a new post.
    # 
    # Returns embed object, ready to be sent. If there is any error while building the embed, the function
    # returns None. The function will not throw any exceptions.
    async def __fmtredditembed(self, subm: asyncpraw.reddit.models.Submission) -> discord.Embed | None:
        embed: discord.Embed = None
        try:
            # Fetch author object.
            author = await self._reddit.redditor(name = subm.author.name, fetch = True)

            # Construct title and body preview. If they exceed a certain number of characters, they will be shortened.
            # If the post is marked as a spoiler, the body will be obscured using the regular discord spoiler via ||.
            title = subm.title[:self.MTLEN].strip() + '...' if len(subm.title) > self.MTLEN else subm.title
            body  = subm.selftext[:self.MBLEN].strip() + '...' if len(subm.selftext) > self.MBLEN else subm.selftext
            if len(body) > 0 and subm.spoiler:
                body = f'||{body}||'

            # Construct embed.
            embed = kiyo_utils.fmtembed(
                color  = 0xff6314, # reddit orange
                title  = title,
                tstamp = datetime.datetime.fromtimestamp(subm.created_utc),
                desc   = body,
                url    = subm.shortlink 
            ).set_author(
                name = f'{subm.subreddit_name_prefixed}',
                url  = f'https://www.reddit.com/r/{subm.subreddit_name_prefixed[2:]}'
            ).set_footer(
                text     = f'u/{subm.author.name}',
                icon_url = author.icon_img
            )

            # Try to load an embedded image if the post has one. Posts may also have other links that are
            # not images, which will cause the image preview to fail.
            # Sometimes, posts may have unusual keywords instead of an actual URL, trying to load resources from
            # those will fail so we first verify that our submission URL is not actually a reserved keyword.
            if subm.url not in [None, '', 'self', 'default', 'spoiler', 'image']:
                # Only preview images that are from reddit itself, imgur is also fine. Do not send the image preview
                # if the post is marked as a spoiler.
                domain = urlparse(subm.url).netloc
                if any(x in domain for x in ['i.redd.it', 'reddit.com/media', 'i.imgur.com', 'preview.redd.it']) and not subm.spoiler:
                    # It's likely the URL is pointing to an image resource, try to display it.
                    embed.set_image(url = subm.url)
        except Exception as tmp_e:
            # Treat all exceptions as if there was an error with building the embed.
            logger.error(f'Could not build display embed. Reason: {tmp_e}')

            return None

        # Everything went well. Return the constructed embed.
        return embed


    # Retrieves the number of guilds that are subscribed to a given subreddit.
    # If the subreddit is not being listened to (i.e. not in cache), the function
    # returns 0.
    #
    # Returns number of subscribed guilds.
    def __nsubs(self, subn: str) -> int:
        return len(self._data.get(subn, []))


    # This background task now queries all registered sub-reddits and sends the results
    # to all guilds that subscribed to the subs that posted the submissions.
    #
    # Returns nothing.
    @tasks.loop(seconds = 30)
    async def __on_scrape_newsubms(self) -> None:
        # If the feed has not yet been initialized (i.e. no subs are being listened to), just
        # return and try again when the next iteration starts.
        if self._subl is None and len(self._feed) > 0:
           await self.__buildfeed()
        elif self._subl is None:
            return

        # Wait for new submissions to come in any of the subs in the feed.
        newlatest = ''
        latestts  = 0
        try:
            async for subm in self._subl.new():
                # If we are about to process the first time of the current iteration, update
                # the variable that holds the first-processed post of the iteration.
                if newlatest == '':
                    newlatest = subm.id
                    latestts  = int(subm.created)
                # If we are not processing the first post, process new posts as long as we have
                # not reached the latest post of the previous iteration.
                # If there is no latest post (i.e. first iteration of first ever run or no registered
                # subreddits prior to current iteration), simply skip the current iteration to prevent
                # spamming the first subscriber with possibly a ton of posts.
                if subm.id == self._lid or self._lid == '' or int(subm.created) < self._lfupd or int(subm.created) <= self._lts:
                    break

                # Prepare a fancy embed that is then sent to all guilds that have subscribed to the
                # subreddit the post was submitted to.
                try:
                    # Prepare message embed.
                    embed = await self.__fmtredditembed(subm)
                    
                    # Post the embed in every guild that subscribed to the sub the submission was
                    # posted in.
                    sublist = self._data.get(subm.subreddit_name_prefixed[2:], None)
                    for (gid, chan, prole) in sublist or []:
                        try:
                            gchan = self._app.get_guild(gid).get_channel(chan)
                            if gchan is not None:
                                await gchan.send(content = f'<@&{prole}>' if prole != 0 else None, embed = embed)
                        except Exception as tmp_e:
                            logger.error(f'Could not send post to broadcast channel. Reason: {tmp_e}')
                except Exception as tmp_e:
                    # In case there was an issue, like an invalid response or any malformed
                    # data, just skip the post.
                    logger.error(f'Could not send post from subreddit \'{subm.subreddit_name_prefixed}\'. Reason: {tmp_e}')

            # Update 'new latest' post.
            self._lid = newlatest
            self._lts = max(latestts, self._lts)
        except Exception as tmp_e:
            # In case there was an error scraping new submissions, log it.
            logger.error(f'Could not scrape new submissions. Reason: {tmp_e}')



# command group controlling the reddit module, commands in here is only for members
# with the 'manage_guild' permission
@discord.app_commands.guild_only()
@discord.app_commands.default_permissions(manage_guild = True)
class KiyokoCommandGroup_Reddit(discord.app_commands.Group):
    # maximum number of subs a single guild can subscribe to.
    MAXLISTENERS = 8

    def __init__(self, app, name: str, desc: str):
        super().__init__(name = name, description = desc)

        self._app = app
        self._man = KiyokoSubredditManager(app)

        # Read all reddit data from database.
        self._man.initdata()


    # Adds a new sub-reddit listener to the guild. There can be a maximum
    # of MAXLISTENERS subreddits that a guild can listen to.
    #
    # Returns nothing.
    @discord.app_commands.command(name = 'add', description = f'subscribes to a new subreddit (max: {MAXLISTENERS})')
    @discord.app_commands.describe(
        subreddit = 'subreddit that is to be listened to; can be with or without \'r/\'; must be exact',
        broadcast = 'channel to broadcast sub-reddit submissions to',
        role      = 'optional role to ping whenever a submission is posted'
    )
    @discord.app_commands.check(kiyo_utils.isenabled)
    @discord.app_commands.check(kiyo_utils.updcmdstats)
    async def cmd_add(self, inter: discord.Interaction, subreddit: str, broadcast: discord.TextChannel, role: Optional[discord.Role]) -> None:
        # Check if the application has 'send_messages' and 'attach_files' permissions
        # in the given broadcast channel.
        reqperms = discord.Permissions(view_channel = True, embed_links = True, send_messages = True)
        if not kiyo_utils.haschanperms(inter, broadcast, reqperms):
            raise kiyo_error.AppCmd_MissingChannelPermissions

        # Get status of sub.
        (name, status) = await self._man.querysubstatus(inter.guild.id, subreddit.strip())
        
        # If sub can be added, check if we have have not yet hit the maximum
        # number of listeners per guild.
        if status == KiyokoSubredditStatus.AVAILABLE:
            roleid      = role.id if role is not None else 0
            gcfg        = self._app.gcman.getgconfig(inter.guild.id)
            gcfg.reddit = gcfg.reddit or list()

            # If we have hit the maximum, cannot add more. Output an error
            # in that case.
            if len(gcfg.reddit) >= self.MAXLISTENERS:
                raise kiyo_error.AllSlotsOccupied

            # Add sub to listener list.
            gcfg.reddit.append({'id': name, 'broadcast': broadcast.id, 'prole': roleid})
            # Add sub to data storage.
            self._man.addsubreddit(name, inter.guild.id, broadcast.id, roleid)
            # Update subreddit feed.
            await self._man.updfeed((name, True))
            # Update guild config.
            await kiyo_guild.updgsettings(self._app, gcfg)

            # Respond with success message.
            (embed, file) = kiyo_utils.cfgupdembed(
                inter = inter,
                desc  = 'reddit',
                upd   = [],
                extra = f'\n\nSubreddit listener ``#{len(gcfg.reddit)}`` for ``r/{name}`` has been successfully added. '
                        f'``{self.MAXLISTENERS - len(gcfg.reddit)}`` listeners remaining.'
            )
            await kiyo_utils.sendmsgsecure(inter, embed = embed, file = file)
        else:
            raise kiyo_error.AppCmd_InvalidParameter


    # Auto-complete callback for '/reddit rem'; allows the user to choose between
    # subs the guild is actually listening to.
    #
    # Returns list of sub-reddits that the guild is listening to.
    async def __cmd_rem_autocmpl(self, inter: discord.Interaction, current: str) -> typing.List[discord.app_commands.Choice[str]]:
        # Get list of all subs the guild is listening to.
        slist = [x.get('id') for x in self._app.gcman.getgconfig(inter.guild.id).reddit]

        # Compile and return list of available choices.
        return [discord.app_commands.Choice(name = x, value = x) for x in slist]

    # Removes a subreddit listener for a specific guild.
    #
    # Returns nothing.
    @discord.app_commands.command(name = 'rem', description = 'unsubscribes from a specific subreddit')
    @discord.app_commands.describe(subreddit = 'subreddit name to unsubscribe from; must be exact')
    @discord.app_commands.autocomplete(subreddit = __cmd_rem_autocmpl)
    @discord.app_commands.check(kiyo_utils.isenabled)
    @discord.app_commands.check(kiyo_utils.updcmdstats)
    async def cmd_rem(self, inter: discord.Interaction, subreddit: str) -> None:
        subn = subreddit.strip()

        # Try removing the sub listener.
        if self._man.remsubreddit(subn, inter.guild.id):
            # Update guild config cache.
            gcfg = self._app.gcman.getgconfig(inter.guild.id)
            gcfg.reddit = [x for x in gcfg.reddit if x.get('id') != subn]
            # Update feed.
            await self._man.updfeed((subn, False))
            # Update guild settings in db.
            await kiyo_guild.updgsettings(self._app, gcfg)

            # Prepare and send confirmation message.
            (embed, file) = kiyo_utils.cfgupdembed(
                inter = inter,
                desc  = 'reddit',
                upd   = [],
                extra = f'\n\nSubreddit listener for ``r/{subn}`` has been successfully removed. '
                        f'``{self.MAXLISTENERS - len(gcfg.reddit)}`` listeners available.'
            )
            await kiyo_utils.sendmsgsecure(inter, embed = embed, file = file)
        else:
            raise kiyo_error.AppCmd_InvalidParameter



    # Lists all active subreddit listeners for a given guild.
    #
    # Returns nothing.
    @discord.app_commands.command(name = 'list', description = 'lists all active subreddit listeners for the current guild')
    @discord.app_commands.check(kiyo_utils.isenabled)
    @discord.app_commands.check(kiyo_utils.updcmdstats)
    async def cmd_list(self, inter: discord.Interaction) -> None:
        # Get guild config for current guild.
        gcfg = self._app.gcman.getgconfig(inter.guild.id)

        # Enumerate a string that contains all active subreddit listeners.
        nlisten = 1
        extra   = f'Active subreddit listeners for guild ``{inter.guild.name}`` (id: ``{inter.guild.id}``):\n'
        for entry in gcfg.reddit or []:
            role = f'<@&{entry["prole"]}>' if entry['prole'] != 0 else '``not set``'
            extra += f'\n{nlisten}. ``r/{entry["id"]}``; bc: <#{entry["broadcast"]}>; role: {role}'

            nlisten += 1

        # If there are no active listeners, show an info message.
        if nlisten == 1:
            extra += '\nCould not find any active subreddit listeners.'

        # Prepare and send response.
        (embed, file) = kiyo_utils.fmtcfgviewembed(
            inter = inter,
            desc  = extra
        )
        await kiyo_utils.sendmsgsecure(inter, file = file, embed = embed)



# module entrypoint
async def setup(app) -> None:
    # Initialize 'reddit' module.
    cmdgroup = None
    try:
        cmdgroup = KiyokoCommandGroup_Reddit(
            app,
            name = 'reddit',
            desc = 'manages the subreddit streaming module'
        )
    except Exception as tmp_e:
        logger.error(f'Failed to initialize \'reddit\' module. Reason: {tmp_e}')

        return

    # If everything went well, add the command to the tree.
    app.tree.add_command(cmdgroup)


