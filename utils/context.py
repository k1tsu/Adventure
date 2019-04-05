# -> Builtin modules
import asyncio

# -> Pip packages
import discord
from discord.ext import commands
from jishaku.paginators import PaginatorEmbedInterface, WrappedPaginator

# -> Local files
import blobs


class EpicContext(commands.Context):
    def __repr__(self):
        return "<EpicContext author={0.author} channel={0.channel} guild={0.guild}>".format(self)

    async def send(self, content=None, **kwargs):
        try:
            await super().send(content, **kwargs)
        except discord.HTTPException as e:
            if e.code == 400:
                pass
            raise

    async def invoke(self, *args, **kwargs):
        try:
            ret = await super().invoke(*args, **kwargs)
        except Exception as e:
            self.bot.dispatch("command_error", self, e)
        else:
            self.bot.dispatch("command_completion", self)
            return ret
        finally:
            self.bot.dispatch("command", self)

    async def add_reaction(self, emote):
        try:
            await self.message.add_reaction(emote)
        except discord.Forbidden:
            pass

    async def safe_delete(self):
        try:
            await self.message.delete()
            return True
        except discord.Forbidden:
            return False

    async def paginate(self, *words):
        embed = discord.Embed(color=discord.Colour.blurple())
        pg = WrappedPaginator(prefix="", suffix="", max_size=2048)
        for line in words:
            pg.add_line(line)
        inf = PaginatorEmbedInterface(self.bot, pg, owner=self.author, embed=embed)
        await inf.send_to(self)

    async def warn(self, message, *, waiter=None):
        self.bot.confirmation_invocation.append(self.author.id)
        waiter = waiter or self.author
        msg = await super().send(message)
        await msg.add_reaction(blobs.BLOB_TICK)
        await msg.add_reaction(blobs.BLOB_CROSS)

        def warn_check(r, u):
            return str(r) in (str(blobs.BLOB_TICK), str(blobs.BLOB_CROSS)) and u == waiter

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=warn_check, timeout=10.0)
        except asyncio.TimeoutError:
            return False
        else:
            return str(reaction) == str(blobs.BLOB_TICK)
        finally:
            await msg.delete()
            self.bot.confirmation_invocation.remove(self.author.id)
