import asyncio

import discord
from discord.ext import commands


class Support(commands.Cog):
    """
    Commands that may only be used by supporters.
    You can't become a supporter currently, they are just my beta testers.
    """
    def __init__(self, bot):
        self.bot = bot
        self.guild = self.bot.get_guild(561390061963182132)
        self.dehoist_role = self.guild.get_role(561405074585157693) if self.guild else None
        self.channel = self.bot.get_channel(561390634863165450)
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
        self.channel = self.bot.get_channel(561390634863165450)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.channel.send(f"Joined guild {guild} [{guild.id}] owned by {guild.owner}.\n"
                                f"{guild.member_count} | {len(list(filter(lambda m: m.bot, guild.members)))} Bots | "
                                f"{len(list(filter(lambda m: not m.bot, guild.members)))} Members")



def setup(bot):
    bot.add_cog(Support(bot))
