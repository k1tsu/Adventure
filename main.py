# -> Builtin modules
import asyncio
import logging
import os
import sys
from datetime import datetime

# -> Requires Python 3.6.x - 3.7.x
if sys.version_info[0] < 3 or not (6 <= sys.version_info[1] <= 7):
    raise RuntimeError("Only usable with Python 3.6.x or Python 3.7.x")

# -> This is required prior to importing "jishaku"
if sys.platform == "win32":
    os.environ['SHELL'] = r"C:\Windows\System32\bash.exe"
os.environ['JISHAKU_HIDE'] = "true"

# -> Pip packages
import aioredis
import asyncpg
import discord
from discord.ext import commands
from jishaku import shell as jskshell

# -> Local files
import config
import utils

jskshell.WINDOWS = False


ANSI_RESET = "\33[0m"

ANSI_COLOURS = {
    "WARNING": "\33[93m",
    "INFO": "\33[96m",
    "DEBUG": "\33[95m",
    "ERROR": "\33[91m",
    "CRITICAL": "\33[91m"
}


class ColouredFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("[%(asctime)s %(name)s/%(levelname)s]: %(message)s", "%H:%M:%S")

    def format(self, record: logging.LogRecord):
        levelname = record.levelname
        record.msg = ANSI_COLOURS[levelname] + record.msg + ANSI_RESET
        return super().format(record)


stream = logging.StreamHandler()
stream.setFormatter(ColouredFormatter())

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s %(name)s/%(levelname)s]: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("logs/adventure.log", "w", encoding='UTF-8'),
        stream
    ]
)
try:
    logging.getLogger("discord.client").disabled = True
    logging.getLogger("discord.http").disabled = True
    logging.getLogger("discord.gateway").disabled = True
    logging.getLogger("discord.state").disabled = True
    logging.getLogger("asyncio").disabled = True
    logging.getLogger("websockets.protocol").disabled = True
    logging.getLogger("aioredis").disabled = True
finally:
    pass
log = logging.getLogger("Adventure.main")
# log.setLevel(logging.DEBUG)
log.info("="*20 + "BOOT @ " + datetime.utcnow().strftime("%d/%m/%y %H:%M") + "="*30)
log.warning("WARN TEST")
log.debug("DEBUG TEST")
log.info("INFO TEST")
log.error("ERROR TEST")
log.critical("CRITICAL TEST")

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    log.info("uvloop installed and running.")
except ImportError:
    if sys.platform == 'linux':
        log.warning("The host is running Linux but uvloop isn't installed.")
    uvloop = None


EXTENSIONS = [
    "jishaku",
    "cogs.error_handler",
    "cogs.help",
    "cogs.misc",
    "cogs.moderators",
    "objectmanagers.players",
    "objectmanagers.maps"
]


class Adventure(commands.Bot):
    def __init__(self):
        super().__init__(self.getprefix)
        # noinspection PyProtectedMember
        self.session = self.http._session
        self.config = config
        self.prepared = asyncio.Event(loop=self.loop)
        self.unload_complete = list()
        self.blacklist = dict()
        self.add_check(self.blacklist_check)
        self.prepare_extensions()

    async def blacklist_check(self, ctx):
        if ctx.author.id in self.blacklist:
            raise utils.Blacklisted(self.blacklist[ctx.author.id])
        return True

    def prepare_extensions(self):
        for extension in EXTENSIONS:
            try:
                self.load_extension(extension)
                log.info("%s loaded successfully.", extension)
            except Exception as e:
                log.critical("%s failed to load [%s: %s]", extension, type(e).__name__, str(e))

    async def is_owner(self, user):
        return user.id in config.OWNERS

    # noinspection PyUnusedLocal
    async def getprefix(self, *args):
        if not self.prepared.is_set():
            return commands.when_mentioned(*args)
        return commands.when_mentioned_or(config.PREFIX)(*args)

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=utils.EpicContext)

    # noinspection PyAttributeOutsideInit
    async def on_ready(self):
        if self.prepared.is_set():
            return
        self.redis = await aioredis.create_pool(config.REDIS_ADDRESS)
        log.info("Connected to Redis server.")
        self.db = await asyncpg.create_pool(**config.ASYNCPG)
        async with self.db.acquire() as cur:
            with open("schema.sql") as f:
                await cur.execute(f.read())
            for userid, reason in await cur.fetch("SELECT user_id, reason FROM blacklist;"):
                if not self.get_user(userid):
                    log.warning("Blacklisted ID \"%s\" is unknown.", userid)
                    # await cur.execute("DELETE FROM blacklist WHERE userid=$1;", userid)
                self.blacklist[userid] = reason
                log.info("User %s (%s) is blacklisted.", self.get_user(userid), userid)
        log.info("Connected to PostgreSQL server.")

        self.player_manager = self.get_cog("PlayerManager")
        self.map_manager = self.get_cog("MapManager")

        self.prepared.set()
        log.info("Setup complete. Listening to commands on prefix \"%s\".", config.PREFIX)
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                             name=f"*help"))

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
        for event in self.unload_complete:
            await event.wait()
        await self.db.close()
        self.redis.close()
        await self.redis.wait_closed()
        await super().logout()

    def run(self, token):
        loop = self.loop
        try:
            loop.run_until_complete(self.start(token))
        except KeyboardInterrupt:
            loop.run_until_complete(self.logout())


# https://discordapp.com/channels/336642139381301249/381963689470984203/543337687797727242
# :rooThink:


Adventure().run(config.TOKEN)
