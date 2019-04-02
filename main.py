# -> Builtin modules
import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime

# -> Requires Python 3.6.x - 3.7.x
if sys.version_info[0] < 3 or not (6 <= sys.version_info[1] <= 7):
    raise RuntimeError("Only usable with Python 3.6.x or Python 3.7.x")

# -> This is required prior to importing "jishaku"
if sys.platform == "win32":
    os.environ['SHELL'] = r"C:\Windows\System32\bash.exe"
os.environ['JISHAKU_HIDE'] = "true"

# -> Pip packages
import aiohttp
import aioredis
import asyncpg
import dbl
import discord
import psutil
from discord.ext import commands
from jishaku import shell as jskshell

try:
    import uvloop
except ImportError:
    uvloop = None
    if sys.platform in ("linux", "darwin"):
        print("Platform is a linux distribution, but uvloop isn't installed!", file=sys.stderr)
    else:
        asyncio.set_event_loop(asyncio.ProactorEventLoop())
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
del uvloop

try:
    from discord.ext import colours
    # this is just a loader in case you installed `discord-ext-colours`
except ImportError:
    pass


# -> Local files
import config
import utils

jskshell.WINDOWS = False


INIT = datetime.utcnow()
FILE_NAME = f"logs/{INIT.strftime('%Y-%m-%d_%H.%M.%S.%f')}.log"

log = logging.getLogger("Adventure.main")


def extensions():
    n = []
    n.extend([f'cogs.{f[:-3]}' for f in os.listdir("cogs") if not f.startswith("__")])
    n.extend([f'objectmanagers.{f[:-3]}' for f in os.listdir("objectmanagers") if not f.startswith("__")])
    return n


EXTENSIONS = extensions()


class Adventure(commands.Bot):
    def __init__(self):
        super().__init__('//')
        # noinspection PyProtectedMember
        self.session = aiohttp.ClientSession()
        self.config = config
        self.prepared = asyncio.Event(loop=self.loop)
        self.unload_complete = []
        self.blacklist = {}
        self.in_tutorial = []
        self.player_manager = None
        self.map_manager = None
        self.item_manager = None
        self.enemy_manager = None
        self.dbl_client = dbl.Client(self, self.config.DBL)
        self.prefixes = {}
        self.process = psutil.Process()
        self.init = INIT
        self.internal_webhook_handler = None
        self.add_check(self.blacklist_check)
        self.prepare_extensions()

    async def blacklist_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        if ctx.author.id in self.blacklist:
            #raise utils.Blacklisted(self.blacklist[ctx.author.id])
            raise utils.IgnoreThis
        if ctx.channel.id in self.player_manager.ignored_channels:
            raise utils.IgnoreThis
        if ctx.guild.id in self.player_manager.ignored_guilds:
            raise utils.IgnoreThis
        if ctx.author.id in self.in_tutorial:
            raise utils.IgnoreThis
        return True

    def dispatch(self, event, *args, **kwargs):
        if not self.prepared.is_set() and event in ("message", "command", "command_error"):
            return  # this is to prevent events like on_message, on_command etc to be sent out before im ready to start
        return super().dispatch(event, *args, **kwargs)

    async def get_supporters(self):
        return [self.get_user(u['userid']) for u in await self.db.fetch("SELECT userid FROM supporters;")]

    def prepare_extensions(self):
        for extension in EXTENSIONS:
            try:
                self.load_extension(extension)
                log.info("%s loaded successfully.", extension)
            except Exception as e:
                log.critical("%s failed to load [%s: %s]", extension, type(e).__name__, str(e))

    async def is_owner(self, user):
        return user.id in config.OWNERS

    def prefixes_for(self, guild: discord.Guild):
        if guild:
            return self.prefixes.get(guild.id, set())
        else:
            return set(config.PREFIX)

    # noinspection PyUnusedLocal
    async def getprefix(self, bot, msg):
        if not self.prepared.is_set():
            return commands.when_mentioned(bot, msg)
        prefixes = set(config.PREFIX)
        prefixes |= self.prefixes_for(msg.guild)
        return commands.when_mentioned_or(*prefixes)(bot, msg)

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=utils.EpicContext)

    async def redis(self, *args, **kw):
        try:
            return await self._redis.execute(*args, **kw)
        except aioredis.errors.PoolClosedError:
            return

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.author.id not in self.config.OWNERS:
            return
        if self.user in message.mentions:
            try:
                await message.add_reaction("\N{EYES}")
            except discord.HTTPException:
                pass
        await self.process_commands(message)

    # noinspection PyAttributeOutsideInit
    async def on_ready(self):
        if self.prepared.is_set():
            return

        self._redis = await asyncio.wait_for(aioredis.create_pool(config.REDIS_ADDRESS, password=config.REDIS_PASS),
                                             timeout=20.0)
        log.info("Connected to Redis server.")
        self.db = await asyncpg.create_pool(**config.ASYNCPG)
        log.info("Connected to PostgreSQL server.")

        for guild in self.guilds:
            prefix = set(map(bytes.decode, await self.redis("SMEMBERS", f"prefixes_{guild.id}")))
            if not prefix:
                prefix = set(config.PREFIX)
            self.prefixes[guild.id] = prefix

        async with self.db.acquire() as cur:
            with open("schema.sql") as f:
                await cur.execute(f.read())
            for userid, reason in await cur.fetch("SELECT user_id, reason FROM blacklist;"):
                if not self.get_user(userid):
                    log.warning("Blacklisted ID \"%s\" is unknown.", userid)
                    # await cur.execute("DELETE FROM blacklist WHERE userid=$1;", userid)
                self.blacklist[userid] = reason
                log.info("User %s (%s) is blacklisted.", self.get_user(userid), userid)

        self.prepared.set()
        log.info("Setup complete. Listening to commands on prefix \"%s\".", config.PREFIX)
        await self.change_presence(activity=discord.Game(name="Use *tutorial to begin!"))

    async def on_error(self, event, *args, **kwargs):
        error = traceback.format_exc()
        self.dispatch("event_error", event, error, *args, **kwargs)

    async def start(self, token):
        await self.login(token, bot=True)
        await self.connect(reconnect=True)

    async def logout(self):
        log.info("logout() called. Closing down.")
        self.dispatch("logout")
        self.prepared.clear()
        async with self.db.acquire() as cur:
            await cur.execute("DELETE FROM blacklist;")
            for userid, reason in self.blacklist.items():
                await cur.execute("INSERT INTO blacklist VALUES ($1, $2);", userid, reason)
                # update because using *blacklist should automatically add them to the db
        for guildid, prefixes in self.prefixes.items():
            await self.redis("DEL", f"prefixes_{guildid}")
            await self.redis("SADD", f"prefixes_{guildid}", *prefixes)
        for event in self.unload_complete:
            try:
                await asyncio.wait_for(event.wait(), timeout=60.0)
            except asyncio.TimeoutError:
                log.critical("Event %r failed to finish in time.", event)
        await self._redis.execute_pubsub("UNSUBSCRIBE", "vote-channel")
        try:
            self.internal_webhook_handler.cancel()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.critical("Fatal error when closing hook server| %s: %s", type(e).__name__, e)
        await self.db.close()
        self._redis.close()
        await self._redis.wait_closed()
        await super().logout()

    def run(self):
        loop = self.loop
        try:
            loop.run_until_complete(self.start(config.TOKEN))
        except KeyboardInterrupt:
            loop.run_until_complete(self.logout())


# https://discordapp.com/channels/336642139381301249/381963689470984203/543337687797727242
# :rooThink:


def main(run=True):
    ANSI_RESET = "\33[0m"

    ANSI_COLOURS = {
        "WARNING": "\33[93m",
        "DEBUG": "\33[96m",
        "ERROR": "\33[91m",
        "CRITICAL": "\33[95m"
    }

    class ColouredFormatter(logging.Formatter):
        def __init__(self):
            super().__init__("[%(asctime)s %(name)s/%(levelname)s]: %(message)s", "%H:%M:%S")

        def format(self, record: logging.LogRecord):
            levelname = record.levelname
            msg = super().format(record)
            if levelname == "INFO":
                return msg
            return ANSI_COLOURS[levelname] + msg + ANSI_RESET

    handler = logging.StreamHandler()
    handler.setFormatter(ColouredFormatter())

    filehandler = logging.FileHandler(FILE_NAME, "w", encoding='UTF-8')

    log.handlers = [filehandler, handler]
    log.setLevel(logging.DEBUG)

    for logger in [
        "Adventure.cogs.ErrorHandler", "Adventure.cogs.Help", "Adventure.cogs.Moderator",
        "Adventure.EnemyManager", "Adventure.ItemManager", "Adventure.MapManager", "Adventure.PlayerManager"
    ]:
        logg = logging.getLogger(logger)
        logg.handlers = [filehandler, handler]
        logg.setLevel(logging.DEBUG)

    log.info("=" * 20 + "BOOT @ " + datetime.utcnow().strftime("%d/%m/%y %H:%M") + "=" * 20)

    if run:
        Adventure().run()


if __name__ == "__main__":
    main()
