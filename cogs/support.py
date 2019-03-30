import asyncio

import discord
from discord.ext import commands


class Support(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = self.bot.get_guild(561390061963182132)
        self.dehoist_role = self.guild.get_role(561405074585157693)
        self.member_role = self.guild.get_role(561404610070183936)
        self.dehoist_task: asyncio.Task = self.bot.loop.create_task(self.dehoisting())

    def cog_unload(self):
        try:
            self.dehoist_task.cancel()
        except asyncio.CancelledError:
            pass

    async def dehoisting(self):
        await self.bot.wait_until_ready()
        while True:
            for member in self.guild.members:
                if member.display_name[0] in list(map(chr, range(33, 48))):
                    await member.edit(nick="💩")
                    await member.add_roles(self.dehoist_role)
            await asyncio.sleep(7200)

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(561390061963182132)
        self.dehoist_role = self.guild.get_role(561405074585157693)
        self.member_role = self.guild.get_role(561404610070183936)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild != self.guild:
            return
        await member.add_roles(self.member_role)


def setup(bot):
    bot.add_cog(Support(bot))
