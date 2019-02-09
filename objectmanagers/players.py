from discord.ext import commands
import discord

import utils
import blobs

import asyncio
from datetime import datetime
import logging
log = logging.getLogger("Adventure.PlayerManager")


class MapConverter(commands.Converter):
    async def convert(self, ctx, argument):
        return ctx.bot.map_manager.resolve_map(argument)


class PlayerManager:
    def __init__(self, bot):
        self.bot = bot
        self.players = list()
        self.unload_event = asyncio.Event()
        self.bot.unload_complete.append(self.unload_event)
        self.is_creating = []

    def __repr__(self):
        return "<PlayerManager players={0}>".format(len(self.players))

    async def on_command(self, ctx):
        player = self.get_player(ctx.author._user)
        if not player:
            return
        if await player.update_travelling():
            await ctx.send("%s %s returned from their travels!" % (player, blobs.BLOB_PARTY))

    # -- Commands -- #

    @commands.command()
    async def create(self, ctx):
        if ctx.author.id in self.is_creating:
            return
        player = self.get_player(ctx.author._user)
        if player:
            return await ctx.send("You already own \"%s\"!" % player)
        self.is_creating.append(ctx.author.id)
        await ctx.send("%s What should the name be? (Name must be 32 characters or lower in length)" % (blobs.BLOB_O,))

        def msgcheck(m):
            return len(m.content) < 33 and m.author == ctx.author

        try:
            msg = await self.bot.wait_for("message", check=msgcheck, timeout=60.0)
        except asyncio.TimeoutError:
            await ctx.send("Took too long...")
        else:
            msg = await commands.clean_content().convert(ctx, msg.content)
            log.info("Player \"%s\" was created by \"%s\".", msg, ctx.author)
            player = utils.Player(owner=ctx.author._user, name=msg, bot=self.bot, created_at=datetime.utcnow())
            await player.save()
            self.players.append(player)
            await ctx.send("%s Success! \"%s\" was sent to map #0 (Home)." % (blobs.BLOB_PARTY, msg))
        finally:
            self.is_creating.remove(ctx.author.id)

    @commands.command()
    async def delete(self, ctx):
        player = self.get_player(ctx.author._user)
        if not player:
            return await ctx.send("You don't have a player.")
        if await ctx.warn("Are you sure you want to delete \"%s\"? %s" % (player, blobs.BLOB_PLSNO)):
            await player.delete()
            await ctx.send("Goodbye, %s. %s" % (player, blobs.BLOB_SALUTE))

    @commands.command()
    async def travel(self, ctx, *, destination: MapConverter):
        player = self.get_player(ctx.author._user)
        if not player:
            return await ctx.send("You don't have a player! Create one with `%screate`!" % ctx.prefix)
        if not destination:
            return await ctx.send("Unknown map.")
        if destination.id in (-1, 696969):
            return await ctx.send("Unknown map {}".format(blobs.BLOB_WINK))
        if destination not in player.map.nearby:
            raise utils.NotNearby(player.map, destination)
        time = player.map.calculate_travel_to(destination)
        if time > 4500:
            if not await ctx.warn("%s It's a long trip, are you sure you want to go?" % blobs.BLOB_THINK):
                return
        # noinspection PyTypeChecker
        await player.travel_to(destination)
        await ctx.send("%s %s is now travelling to %s and will return in %s hours." %
                       (blobs.BLOB_SALUTE, player.name, destination.name, time))

    @commands.command()
    async def profile(self, ctx: utils.EpicContext, *, member: discord.Member = None):
        member = member or ctx.author
        player = self.get_player(member._user)
        if not player:
            return await ctx.send(f"%s doesn't have a player %s" % (member, blobs.BLOB_PLSNO))
        embed = discord.Embed(color=discord.Colour.blurple())
        embed.set_author(name=str(member), icon_url=member.avatar_url_as(static_format="png", size=32))
        embed.add_field(name="Name", value=player.name)
        embed.add_field(name="Currently At", value=player.map)
        embed.add_field(name="Created At", value=player.created_at.strftime("%d/%m/%y @ %H:%M"), inline=False)
        await ctx.send(embed=embed)

    # -- Player Manager stuff -- #

    def fetch_players(self):
        return self.bot.db.fetch("SELECT * FROM players;")

    def get_player(self, user: discord.User) -> utils.Player:
        return discord.utils.get(self.players, owner=user)

    # -- Events -- #

    def __unload(self):
        self.bot.unload_complete.remove(self.unload_event)

    async def on_ready(self):
        await self.bot.prepared.wait()
        if len(self.players) > 0:
            return
        for owner_id, name, map_id, created in await self.fetch_players():
            player = utils.Player(owner=self.bot.get_user(owner_id), name=name,
                                  bot=self.bot, created_at=created)
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
