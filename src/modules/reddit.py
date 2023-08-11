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
import time, configparser

from loguru import logger



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
    def __init__(self, app):
        self._app  = app
        self._cfg  = dict()

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
                raise #KiyokoRedditConfigFileError(path)
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
        # key:   tuple[str, str]       => [id, name]
        # value: list[tuple[int, int]] => [gid, cid]
        self._data: dict[tuple[str, str], list[tuple[int, int]]] = dict()


    # Uninitialize the 'reddit' instance.
    async def __del__(self):
        await self._reddit.close()



# command group controlling the reddit module
class KiyokoCommandGroup_Reddit(discord.app_commands.Group):
    # maximum number of subs a single guild can subscribe to.
    MAXLISTENERS = 16

    def __init__(self, app, name: str, desc: str):
        super().__init__(name = name, description = desc)

        self._app = app
        self._man = KiyokoSubredditManager(app)


    # Adds a new sub-reddit listener to the guild. There can be a maximum
    # of MAXLISTENERS subreddits that a guild can listen to.
    #
    # Returns nothing.
    @discord.app_commands.command(name = 'add', description = f'subscribes to a new sub-reddit (max: {MAXLISTENERS})')
    @discord.app_commands.describe(
        subreddit = 'name of the sub-reddit that is to be subscribed to',
        channel   = 'channel to broadcast sub-reddit submissions to'
    )
    async def cmd_redditadd(self, inter: discord.Interaction, subreddit: str, channel: discord.TextChannel) -> None:
        pass



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


