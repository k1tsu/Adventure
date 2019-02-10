from discord.ext.commands import Context
from jishaku.paginators import WrappedPaginator, PaginatorEmbedInterface
from discord import Embed, Colour, Forbidden

import blobs

import asyncio


class EpicContext(Context):
    def __repr__(self):
        return "<EpicContext author={0.author} channel={0.channel} guild={0.guild}>".format(self)

    async def add_reaction(self, emote):
        try:
            await self.message.add_reaction(emote)
        except Forbidden:
            pass

    async def safe_delete(self):
        try:
            await self.message.delete()
            return True
        except Forbidden:
            return False

    async def paginate(self, *words):
        embed = Embed(color=Colour.blurple())
        pg = WrappedPaginator(prefix="", suffix="", max_size=2048)
        for line in words:
            pg.add_line(line)
        inf = PaginatorEmbedInterface(self.bot, pg, owner=self.author, embed=embed)
        await inf.send_to(self)

    async def warn(self, message):
        msg = await super().send(message)
        await msg.add_reaction(blobs.BLOB_TICK)
        await msg.add_reaction(blobs.BLOB_CROSS)

        def warn_check(r, u):
            return str(r) in (str(blobs.BLOB_TICK), str(blobs.BLOB_CROSS)) and u == self.author

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=warn_check, timeout=10.0)
        except asyncio.TimeoutError:
            return False
        else:
            return str(reaction) == str(blobs.BLOB_TICK)
        finally:
            await msg.delete()