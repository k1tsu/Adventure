import asyncio
import logging
import typing

import discord
from discord.ext import commands

import utils


log = logging.getLogger("Adventure.ShopManager")


class ShopManager(commands.Cog, name="Shop Manager"):
    def __init__(self, bot):
        self.bot = bot
        self.items: typing.List[utils.Item] = list()
        self.unload = asyncio.Event()
        self.bot.unload_complete.append(self.unload)

    def __repr__(self):
        return "<ShopManager items=[{0}]>".format(len(self.items))

    # -- Internal -- #

    async def create_item(self, name: str, cost: float):
        item = await utils.Item.without_id(self.bot.db, name=name, cost=cost)
        self.items.append(item)
        log.info("Created item %r", item)

    # -- Events -- #

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.prepared.wait()

        for name, cost, _id in await self.bot.db.fetch("SELECT * FROM shop;"):
            n = utils.Item(id=_id, name=name, cost=cost)
            self.items.append(n)
            log.info("Prepared item %r", n)

    @commands.Cog.listener()
    async def on_logout(self):
        async with self.bot.db.acquire() as cur:
            for item in self.items:
                await item.save(cur)
                log.info("Flushed item %r", item)
        self.unload.set()

    # -- Commands -- #

    @commands.command(hidden=True)
    async def shop(self, ctx):
        n = ["```diff"]
        for item in self.items:
            fmt = f"+ {item.name} [{item.id}]\n  ${item.cost}G\n"
            n.append(fmt)
        n.append("```")
        await ctx.send("\n".join(n))


def setup(bot):
    bot.add_cog(ShopManager(bot))
