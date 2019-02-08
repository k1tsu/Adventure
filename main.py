import asyncio
import sys

import config
import utils

import aioredis
import asyncpg
from discord.ext import commands
import discord

import os
os.environ['SHELL'] = r"C:\Windows\System32\bash.exe"
os.environ['JISHAKU_HIDE'] = "true"

from jishaku import shell as jskshell
jskshell.WINDOWS = False

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s %(name)s/%(levelname)s]: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("logs/adventure.log", "w"),
        logging.StreamHandler(sys.stdout)
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

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    log.info("uvloop installed and running.")
except ImportError:
    if sys.platform == 'linux':
        log.warning("The host is running Linux but uvloop isn't installed.")
    uvloop = None


class Adventure(commands.Bot):
    def __init__(self):
        super().__init__(self.getprefix)
        # noinspection PyProtectedMember
        self.session = self.http._session
        self.config = config
        self.prepared = asyncio.Event(loop=self.loop)
        self.unload_complete = list()
        self.tick = discord.PartialEmoji(False, "tickYes", 490607182010777620)
        self.cross = discord.PartialEmoji(False, "tickNo", 490607198443929620)
        self.prepare_extensions()

    def prepare_extensions(self):
        for extension in config.EXTENSIONS:
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
        self.redis = await aioredis.create_pool(config.REDIS_ADDRESS)
        log.info("Connected to Redis server.")
        self.db = await asyncpg.create_pool(**config.ASYNCPG)
        log.info("Connected to PostgreSQL server.")

        self.player_manager = self.get_cog("PlayerManager")
        self.map_manager = self.get_cog("MapManager")

        self.prepared.set()
        log.info("Setup complete. Listening to commands on prefix \"%s\".", config.PREFIX)

    async def start(self, token):
        await self.login(token, bot=True)
        await self.connect(reconnect=True)

    async def logout(self):
        log.info("logout() called. Closing down.")
        self.dispatch("logout")
        self.prepared.clear()
        for event in self.unload_complete:
            # log.debug("waiting logout on %s.", event)
            await event.wait()
        # log.debug("logout wait complete.")
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


Adventure().run(config.TOKEN)
