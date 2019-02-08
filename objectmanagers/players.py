from utils import Player

from discord.ext import commands
import discord

from utils import Player

import asyncio
import logging
log = logging.getLogger("Adventure.PlayerManager")


class PlayerManager:
    def __init__(self, bot):
        self.bot = bot
        self.players = list()
        self.unload_event = asyncio.Event()
        self.salute = discord.PartialEmoji(False, "blobsalute", 543272198463553537)
        self.bot.unload_complete.append(self.unload_event)
        # log.debug("init")

    def __repr__(self):
        return "<PlayerManager players={0}>".format(len(self.players))

    # -- Commands -- #

    @commands.group(invoke_without_command=True)
    async def player(self, ctx):
        raise commands.BadArgument

    @player.command()
    async def create(self, ctx):
        if self.get_player(ctx.author._user):
            return await ctx.send("You already have a player!")
        await ctx.send(":exclamation: What should the name be? (Name must be 32 characters or lower in length)")

        def msgcheck(m):
            return len(m.content) < 33 and m.author == ctx.author

        try:
            msg = await self.bot.wait_for("message", check=msgcheck, timeout=60.0)
        except asyncio.TimeoutError:
            await ctx.send("Took too long...")
        else:
            msg = await commands.clean_content().convert(ctx, msg.content)
            log.info("Player \"%s\" was created by \"%s\".", msg, ctx.author)
            player = Player(owner=ctx.author._user, name=msg, bot=self.bot)
            await player.save()
            self.players.append(player)
            await ctx.send("Success! \"%s\" was sent to map #0 (Home)." % msg)

    @player.command()
    async def delete(self, ctx):
        player = self.get_player(ctx.author._user)
        if await ctx.warn("Are you sure you want to delete \"%s\"?" % player):
            await player.delete()
            await ctx.send("Goodbye, %s. %s" % (player, self.salute))

    # -- Player Manager stuff -- #

    def fetch_players(self):
        return self.bot.db.fetch("SELECT * FROM players;")

    def get_player(self, user):
        return discord.utils.get(self.players, owner=user)

    # -- Events -- #

    def __unload(self):
        self.bot.unload_complete.remove(self.unload_event)

    async def on_ready(self):
        # log.debug("on_ready")
        await self.bot.prepared.wait()
        # log.debug("wait complete")
        for owner_id, name, map_id in await self.fetch_players():
            player = Player(owner=self.bot.get_user(owner_id), name=name, bot=self.bot)
            player.map = map_id
            self.players.append(player)
            log.info("Player \"%s\" (%s) initialized at map \"%s\".", player.name, str(player.owner), player.map)

    async def on_logout(self):
        async with self.bot.db.acquire() as cur:
            for player in self.players:
                await player.save(cursor=cur)
                log.info("Flushed player \"%s\" (%s).", player.name, player.owner)
        self.unload_event.set()


def setup(bot):
    bot.add_cog(PlayerManager(bot))
