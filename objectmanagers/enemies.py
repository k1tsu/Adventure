import asyncio
import logging
from typing import *

from discord.ext import commands

import utils


log = logging.getLogger("Adventure.EnemyManager")


class EnemyManager(commands.Cog, name="Enemy Manager"):
    def __init__(self, bot):
        self.bot = bot
        self.enemies: List[utils.Enemy] = []
        self.unload_event = asyncio.Event()
        self.bot.unload_complete.append(self.unload_event)

    def __repr__(self):
        return "<EnemyManager total: {0}>".format(len(self.enemies))

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.prepared.wait()
        if len(self.enemies) > 0:
            return
        for name, id, maps, tier in await self.bot.db.fetch("SELECT * FROM encounters;"):
            enemy = utils.Enemy(id=id, name=name, maps=[self.bot.map_manager.resolve_map(m) for m in maps], tier=tier)
            self.enemies.append(enemy)
            log.info("Prepared enemy %r", enemy)

    @commands.Cog.listener()
    async def on_logout(self):
        async with self.bot.db.acquire() as cursor:
            q = """INSERT INTO encounters
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (id) DO NOTHING;
            """
            for e in self.enemies:
                await cursor.execute(q, e.name, e.id, [m.id for m in e.maps], e.tier)
        self.unload_event.set()

    def enemies_for(self, map: utils.Map) -> List[utils.Enemy]:
        return list(filter(lambda e: map in e.maps, self.enemies))


def setup(bot):
    cog = EnemyManager(bot)
    bot.add_cog(cog)
    bot.enemy_manager = cog


def teardown(bot):
    bot.enemy_manager = None
