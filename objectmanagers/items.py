import asyncio
import logging
import typing

import discord
from discord.ext import commands

import utils


log = logging.getLogger("Adventure.ShopManager")


class ItemManager(commands.Cog, name="Item Manager"):
    """<:pinkblobpeek:544693608121630721>"""
    def __init__(self, bot):
        self.bot = bot
        self.items = []
        self.unload = asyncio.Event()
        self.bot.unload_complete.append(self.unload)

    def __repr__(self):
        return "<ItemManager total: {0}>".format(len(self.items))

    # -- Internal -- #

    # -- Events -- #

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.prepared.wait()

        if len(self.items) > 0:
            return

        for (_id, name, cost), lr in await self.bot.db.fetch("SELECT * FROM shop;"):
            n = utils.Item(id=_id, name=name, cost=cost)
            self.items.append(n)
            log.info("Prepared item %r", n)

    @commands.Cog.listener()
    async def on_logout(self):
        #async with self.bot.db.acquire() as cur:
        #    for item in self.items:
        #        await item.save(cur)
        #        log.info("Flushed item %r", item)
        self.unload.set()

    # -- Commands -- #

    @commands.command(hidden=True)
    async def shop(self, ctx):
        n = ["```diff"]
        for item in self.items:
            fmt = f"+ {item.name} [{item.id}]\n  {item.cost} G\n"
            n.append(fmt)
        n.append("```")
        await ctx.send("\n".join(n))


def setup(bot):
    cog = ItemManager(bot)
    bot.add_cog(cog)
    bot.item_manager = cog


def teardown(bot):
    bot.item_manager = None
