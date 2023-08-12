################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# reddit.py - stream reddit submissions from your community subreddit
#             to your discord server

# imports
import discord, asyncpraw
import datetime, configparser

from loguru       import logger
from urllib.parse import urlparse

import discord.ext.tasks as tasks

import src.modules.admin as kiyo_admin



# exception for not configured 'redinitpath' field in .env
class KiyokoRedditInitpathError(Exception):
    def __init__(self):
        super().__init__('\'{redinitpath}\' not could not be found in \'.env\'.')


# exception for missing or malformed reddit initialization file
class KiyokoRedditConfigFileError(Exception):
    def __init__(self, file: str):
        super().__init__(f'Reddit initialization file \'{file}\' could not be found or is malformed.')


# class for not properly configured reddit initialization file
class KiyokoRedditConfigError(Exception):
    def __init__(self, file: str):
        super().__init__(f'Reddit initialization file \'{file}\' is not properly configured. (missing/empty fields?).')



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
        self._subl            = None   # subreddit listener

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
        # value: list[tuple[int, int]] => [gid, cid]
        self._data: dict[str, list[tuple[int, int]]] = dict()

        # Start the stream.
        self.on_scrape_newsubms.start()


    # Uninitialize the 'reddit' instance.
    async def __del__(self):
        await self._reddit.close()


    # Initializes the data-structure. This has to be done after the module
    # has been loaded because of the fact that guild configs get loaded after
    # modules.
    #
    # Returns nothing.
    def initdata(self) -> None:
        # Go through all guild configs and populate the data-structure.
        for gcfg in self._app.gcman.guildconfigs():
            # Get guild-specific reddit config.
            redlist = gcfg.reddit
            if redlist is None:
                continue

            # Populate data-structure.
            for sname in [entry['name'] for entry in redlist]:
                # Create subreddit entry if it does not exist.
                existing = self._data.get(sname)
                if existing is None:
                    self._feed.add(sname)
                    self._data[sname] = list()

                # Add guild info to current sub entry.
                self._data[sname].append((gcfg.gid, 0))


    # Checks if the given sub is globally blacklisted, and if yes, returns True, else False.
    # If the sub does not exist, the function returns -1.
    #
    # Returns 1 if blacklisted, else 0.
    async def issubblisted(self, name: str) -> int:
        # Check if sub exists.
        try:
            sub = await self._reddit.subreddit(name)
            if sub is None:
                return -1
        except:
            # Treat exceptions as if the sub does not exist.
            return -1

        # Check if the sub is blacklisted. If yes, return 
        return name in self._blist


    # Tries to find the given sub name in the feed. If it exists, return True else return False.
    #
    # Returns whether sub exists in feed.
    def issubinfeed(self, name: str) -> bool:
        return name in self._feed


    # Gets the number of subs a given guild is currently listening to.
    #
    # Returns number.
    def getnsubs(self, gid) -> int:
        return sum((gid in dict(entries)) for entries in self._data.values())


    # Checks whether the guild is currently subscribed to the given subreddit.
    #
    # Returns True if the guild is subscribed to the given sub,
    # False if not.
    def isguildsubbed(self, gid: int, name: str) -> bool:
        # Get subreddit entry.
        entry = self._data.get(name)
        if entry is None:
            return False

        # Check if guild is listening to the sub.
        return gid in dict(entry)


    # Updates the feed of the subreddit stream. This happens whenever a guild adds
    # a previously non-tracked subreddit to the manager.
    #
    # Returns nothing.
    async def updfeed(self, upd: list[tuple[str, bool]]) -> None:
        # Add (if they do not already exist in the feed) or remove (if there are no more guilds listening) the given subs.
        for item in upd:
            (sname, isadd) = item

            # If given sub is blacklisted, do not attempt to add. Attempting to remove it is also nonsensical because
            # they cannot be added in the first place.
            try:
                self._feed.add(sname) if isadd and sname not in self._blist else self._feed.remove(sname)
            except KeyError:
                # If the sub entry does not exist, 'remove' will throw a KeyError. Because it's not really important,
                # we just catch and ignore the exception.
                pass

        # Rebuild feed.
        try:
            self._subl = await self._reddit.subreddit('+'.join(self._feed))
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
            title = subm.title[:self.MTLEN] + '...' if len(subm.title) > self.MTLEN else subm.title
            body  = subm.selftext[:self.MBLEN] + '...' if len(subm.selftext) > self.MBLEN else subm.selftext
            if len(body) > 0 and subm.spoiler:
                body = f'||{body}||'

            # Construct embed.
            embed = kiyo_admin.fmtembed(
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
                # Check if 'image' url is a common video platform. If that's the case, do not set the image.
                # This will be extended in the future to exclude even more links that point to resources that
                # cannot be reliably displayed in a Discord embed.
                domain = urlparse(subm.url).netloc
                if not any(x in domain for x in ['youtu', 'tiktok', 'vimeo']):
                    embed.set_image(url = subm.url)
        except Exception as tmp_e:
            # Treat all exceptions as if there was an error with building the embed.
            logger.error(f'Could not build display embed. Reason: {tmp_e}')

            return None

        # Everything went well. Return the constructed embed.
        return embed


    # This background task now queries all registered sub-reddits and sends the results
    # to all guilds that subscribed to the subs that posted the submissions.
    #
    # Returns nothing.
    @tasks.loop(seconds = 5)
    async def on_scrape_newsubms(self) -> None:
        # If the feed has not yet been initialized (i.e. no subs are being listened to), just
        # return and try again when the next iteration starts.
        if self._subl is None:
            return

        # Wait for new submissions to come in any of the subs in the feed.
        newlatest = None
        async for subm in self._subl.new():
            # If we are about to process the first time of the current iteration, update
            # the variable that holds the first-processed post of the iteration.
            if newlatest is None:
                newlatest = subm.id
            # If we are not processing the first post, process new posts as long as we have
            # not reached the latest post of the previous iteration.
            # If there is no latest post (i.e. first iteration of first ever run or no registered
            # subreddits prior to current iteration), simply skip the current iteration to prevent
            # spamming the first subscriber with possibly a ton of posts.
            elif subm.id == self._lid or self._lid == '':
                break

            # Prepare a fancy embed that is then sent to all guilds that have subscribed to the
            # subreddit the post was submitted to.
            try:
                # Prepare message embed.
                embed = await self.__fmtredditembed(subm)
                
                # Post the embed in every guild that subscribed to the sub the submission was
                # posted in.
                #for entry in self._data[subm.subreddit.name]:
                #logger.debug(f'cr: {subm.created_utc} == New Subreddit Post: Sub: {subm.subreddit_name_prefixed}, Name: {subm.title}, Id: {subm.id}')
                chan: discord.abc.TextChannel = self._app.get_guild(1122607253967622297).get_channel(1122607253967622300)
                await chan.send(embed = embed)
            except:
                # In case there was an issue, like an invalid response or any malformed
                # data, just skip the post.
                continue

            # Create embed title and description, shortening them if necessary.


        # Update 'new latest' post.
        self._lid = newlatest



# command group controlling the reddit module
class KiyokoCommandGroup_Reddit(discord.app_commands.Group):
    # maximum number of subs a single guild can subscribe to.
    MAXLISTENERS = 8

    def __init__(self, app, name: str, desc: str):
        super().__init__(name = name, description = desc)

        self._app = app
        self._man = KiyokoSubredditManager(app)


    # Initializes the data-structure by calling the internal init function of
    # the KiyokoSubredditManager instance.
    #
    # Returns nothing.
    def initdata(self) -> None:
        self._man.initdata()


    # Adds a new sub-reddit listener to the guild. There can be a maximum
    # of MAXLISTENERS subreddits that a guild can listen to.
    #
    # Returns nothing.
    @discord.app_commands.command(name = 'add', description = f'subscribes to a list of sub-reddits (max: {MAXLISTENERS})')
    @discord.app_commands.describe(
        subreddits = 'comma-separated list of subreddits to start listening to, with or without \'r/\'',
        broadcast  = 'channel to broadcast sub-reddit submissions to'
    )
    async def cmd_redditadd(self, inter: discord.Interaction, subreddits: str, broadcast: discord.TextChannel) -> None:
        # Check if user has administrator permissions.
        if not await kiyo_admin.helper_hasperms(self._app, 'reddit add', inter, inter.user, discord.Permissions(administrator = True)):
            return
        
        # Check if the application has 'send_messages' and 'attach_files' permissions
        # in the given broadcast channel.
        appperms = broadcast.permissions_for(inter.guild.get_member(inter.client.user.id))
        if not appperms.send_messages or not appperms.attach_files:
            await kiyo_admin.cmderrembed(
                self._app,
                inter = inter,
                cmd   = 'reddit add',
                type  = kiyo_admin.KiyokoAppCommandError.AINSUFFPERMS,
                desc  = f'The application needs to have ``Send Messages`` and ``Attach Files`` permissions in <#{broadcast.id}>.'
            )

            return

        # Compile the list of subs that can be added to the feed. Take into consideration the maximum number
        # of registerable subs per guild and which subs are blacklisted.
        slist = [(x, True) for x in subreddits.strip().replace(' ', '').split(',') if not await self._man.issubblisted(x)]
        await self._man.updfeed(slist)

        try:
            await inter.response.send_message(f'Added {slist}.')
        except:
            pass
        #naddable = self.MAXLISTENERS - self._man.getnsubs(inter.guild.id)
        #flist    = [x for x in subreddits.strip().replace(' ', '').split(',') if await self._man.issubblisted(x) == 0 and not self._man.issubinfeed(x)]



# module entrypoint
async def setup(app) -> None:
    # Initialize 'reddit' module.
    cmdgroup = None
    try:
        cmdgroup = KiyokoCommandGroup_Reddit(
            app,
            name = 'reddit',
            desc = 'manages the sub-reddit streaming module'
        )
    except Exception as tmp_e:
        logger.error(f'Failed to initialize \'reddit\' module. Reason: {tmp_e}')

        return

    # If everything went well, add the command to the tree.
    app.tree.add_command(cmdgroup)


