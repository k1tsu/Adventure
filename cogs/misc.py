from discord.ext import commands
import discord

import typing
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
    async def avatar(self, ctx, *, member: typing.Union[discord.Member, discord.User] = None):
        member = member or ctx.author
        embed = discord.Embed(color=discord.Colour.blurple())
        embed.set_author(name=str(member), icon_url=member.avatar_url_as(format="png", size=32))
        embed.set_image(url=member.avatar_url_as(static_format="png"))
        await ctx.send(embed=embed)

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
