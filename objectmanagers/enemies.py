import asyncio
import logging
import random
from typing import *

from discord.ext import commands

import blobs
import utils


log = logging.getLogger("Adventure.EnemyManager")


class EnemyManager(commands.Cog, name="Enemy Manager"):
    def __init__(self, bot):
        self.bot = bot
        self.enemies: List[utils.Enemy] = []
        self.unload_event = asyncio.Event()
        self.bot.unload_complete.append(self.unload_event)

    def cog_unload(self):
        self.bot.unload_complete.remove(self.unload_event)

    def __repr__(self):
        return "<EnemyManager total: {0}>".format(len(self.enemies))

    @commands.command(ignore_extra=False)
    @commands.cooldown(5, 300, commands.BucketType.user)
    async def encounter(self, ctx):
        """Searches for an enemy to fight within the area.

        Remember that there are no enemies in `Abel`.
        You can only encounter 2 enemies every 60 seconds.
        If you encounter an enemy you cannot fight, you will run away unharmed.
        If you encounter an enemy and fail to defeat it, you will be knocked out
        \u200b\tand magically teleported back to Abel by a mysterious god.
        If you encounter an enemy and defeat it, you will gain Experience."""
        # i need to put a dumb typehint here because pycharm thinks player.map is an int
        player: utils.Player = self.bot.player_manager.get_player(ctx.author)
        if not player:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("You don't have a player! {} Create one with `{}create`!".format(blobs.BLOB_PLSNO,
                                                                                                   ctx.prefix))
        if await player.is_exploring() or await player.is_travelling():
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"{blobs.BLOB_ARMSCROSSED} You are busy! Wait until you are idling before you "
                                  f"try to perform this action.")
        if not player.has_explored(player.map):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("{} You must explore the current map first!".format(blobs.BLOB_ARMSCROSSED))
        if player.map.id == 0:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"{blobs.BLOB_ARMSCROSSED} There are no enemies in Abel!")
        enemies = self.enemies_for(player.map)
        if not enemies:
            log.debug("2.5")
            raise RuntimeError(f"No enemies were discovered for map {player.map!r}")
        strongest = max(enemies, key=lambda e: e.tier)
        chance = 100 + ((len(enemies) - strongest.tier) - player.level)
        if random.randint(0, 100) < chance:
            enemy = random.choice(enemies)
            if enemy.tier > player.level:
                await ctx.send(f"{blobs.NOTLIKE_BLOB} You encountered a **{enemy.name}** but it's too powerful!"
                               f"\nYou ran away to avoid injury.")
            else:
                if enemy.defeat(player.level):
                    exp = random.randint((enemy.tier**3)//8, (enemy.tier**3)//4) + 1
                    await ctx.send(f"{blobs.BLOB_CHEER} You encountered a **{enemy.name}** and defeated it!\n"
                                   f"You gained **{exp}** experience points!")
                    # TODO: gain / lose gold on win / loss
                    player.exp += exp
                    if not player.compendium.is_enemy_recorded(enemy):
                        player.compendium.record_enemy(enemy)
                else:
                    player.map = 0
                    await ctx.send(f"{blobs.BLOB_INJURED} You encountered a **{enemy.name}** and failed to defeat it!\n"
                                   f"You were knocked out and magically sent back to Abel.")
        else:
            await ctx.send(f"{blobs.BLOB_PEEK} You couldn't find anything.")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.prepared.wait()
        if len(self.enemies) > 0:
            return
        for name, maps, tier, id in await self.bot.db.fetch("SELECT * FROM encounters;"):
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
