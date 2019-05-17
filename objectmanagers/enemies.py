import logging
import math
import random
from typing import *

from discord.ext import commands

import blobs
import utils


log = logging.getLogger("Adventure.EnemyManager")


class EnemyManager(commands.Cog, name="Enemies"):
    """
    Handles all enemy related actions.
    """
    def __init__(self, bot):
        self.bot = bot
        self.enemies: List[utils.Enemy] = []

    def __repr__(self):
        return "<EnemyManager total: {0}>".format(len(self.enemies))

    @commands.command(hidden=True)
    async def megami(self, ctx, *, name: str):
        name = name.title().replace(" ", "_")
        async with self.bot.session.get("https://megamitensei.fandom.com/wiki/" + name) as get:
            if get.status == 404:
                return await ctx.send("Couldn't find that page.")
        await ctx.send("https://megamitensei.fandom.com/wiki/" + name)

    @commands.command(ignore_extra=False)
    @commands.cooldown(5, 120, commands.BucketType.user)
    async def encounter(self, ctx):
        """Searches for an enemy to fight within the area.

        Remember that there are no enemies in the safe maps.
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
        if player.map.is_safe:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"{blobs.BLOB_ARMSCROSSED} There are no enemies in {player.map.name}!")
        if await player.is_exploring() or await player.is_travelling():
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"{blobs.BLOB_ARMSCROSSED} You are busy! Wait until you are idling before you "
                                  f"try to perform this action.")
        if not player.has_explored(player.map):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("{} You must explore the current map first!".format(blobs.BLOB_ARMSCROSSED))
        enemies = self.enemies_for(player.map)
        if not enemies:
            raise RuntimeError(f"No enemies were discovered for map {player.map!r}")
        strongest = max(enemies, key=lambda e: e.tier)
        chance = 100 + ((len(enemies) - strongest.tier) - player.level)
        if random.randint(0, 100) < chance:
            enemy = random.choice(enemies)
            if not player.compendium.is_enemy_recorded(enemy) and \
                    await ctx.warn(f"{blobs.BLOB_PEEK} You encountered **{enemy.name}**. Would you like to try and"
                                   f" {blobs.BLOB_TICK} capture it, or {blobs.BLOB_CROSS} defeat it?"):
                capture = True
            else:
                capture = False
            if enemy.defeat(player.level):
                if not capture:
                    exp = math.ceil(enemy.tier ** 2 / 2.5)
                    gold = random.randint(enemy.tier * 2, enemy.tier * 6)
                    player.exp += exp
                    player.gold += gold
                    await ctx.send(f"{blobs.BLOB_CHEER} You encountered **{enemy.name}** and defeated it!\n"
                                   f"You gained **{exp}** experience points and **{gold}** coins!")
                else:
                    await ctx.send(f"{blobs.BLOB_CHEER} You captured **{enemy.name}**!\n")
                    player.compendium.record_enemy(enemy)
            else:
                if not capture:
                    player.map = 0
                    gold = random.randint(enemy.tier * 2, enemy.tier * 6)
                    player.gold = max(0, player.gold - gold)
                    await ctx.send(f"{blobs.BLOB_INJURED} You encountered **{enemy.name}** and failed to defeat it!"
                                   f"\nYou were knocked out, lost {gold} coins and was magically sent back to Abel.")
                else:
                    await ctx.send(f"{blobs.BLOB_SAD} You failed to capture **{enemy.name}**.")
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

    def enemies_for(self, map: utils.Map) -> List[utils.Enemy]:
        return list(filter(lambda e: map in e.maps, self.enemies))


def setup(bot):
    cog = EnemyManager(bot)
    bot.add_cog(cog)
