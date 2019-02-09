from discord.ext import commands

import time
import random


class Misc:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def epic(self, ctx):
        await ctx.trigger_typing()
        messages = await ctx.history().filter(
            lambda m: not m.content.startswith("*") and "epic" in m.content.lower() and not m.author.bot
        ).flatten()
        if not messages:
            return await ctx.send("Not epic.")
        await ctx.send(random.choice(messages).jump_url)

    @commands.command()
    async def ping(self, ctx):
        start = time.perf_counter()
        await ctx.author.trigger_typing()
        end = time.perf_counter() - start
        await ctx.send(f":ping_pong: **{end*1000:.2f}ms**")

    @commands.command()
    async def source(self, ctx):
        await ctx.send("<https://github.com/XuaTheGrate/Adventure>")


def setup(bot):
    bot.add_cog(Misc(bot))
