# -> Builtin modules
import asyncio
import copy
import logging
from datetime import datetime

# -> Pip packages
import discord
from discord.ext import commands

# -> Local files
import utils
import blobs

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
            await ctx.send("{} {} has arrived at {}!".format(blobs.BLOB_PARTY, player, player.map))
        elif await player.update_exploring():
            await ctx.send("{} {} has finished exploring {}!".format(blobs.BLOB_PARTY, player, player.map))

    # -- Commands -- #

    @commands.command(ignore_extra=False)
    async def create(self, ctx):
        if ctx.author.id in self.is_creating:
            return
        player = self.get_player(ctx.author._user)
        if player:
            return await ctx.send("{} You already own \"{}\"!".format(blobs.BLOB_ANGERY, player))
        self.is_creating.append(ctx.author.id)
        await ctx.send("{} What should the name be? (Name must be 32 characters or lower in length)".format(
            blobs.BLOB_O))

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
            await ctx.send("{} Success! \"{}\" was sent to map #0 (Abel).".format(blobs.BLOB_PARTY, msg))
        finally:
            self.is_creating.remove(ctx.author.id)

    @commands.command()
    async def delete(self, ctx):
        player = self.get_player(ctx.author._user)
        if not player:
            return await ctx.send("You don't have a player! {} Create one with `{}create`!".format(blobs.BLOB_PLSNO,
                                                                                                   ctx.prefix))
        if await ctx.warn("Are you sure you want to delete \"{}\"? {}".format(player, blobs.BLOB_PLSNO)):
            await player.delete()
            await ctx.send("Goodbye, {}. {}".format(player, blobs.BLOB_SALUTE))

    @commands.command()
    async def travel(self, ctx, *, destination: MapConverter):
        player = self.get_player(ctx.author._user)
        if not player:
            return await ctx.send("You don't have a player! %s Create one with `%screate`!" % (blobs.BLOB_PLSNO,
                                                                                               ctx.prefix))
        if not destination:
            return await ctx.send("Unknown map. Use `{}maps` to view the available maps.".format(ctx.prefix))
        if destination.id in (-1, 696969):
            return await ctx.send("Unknown map {}".format(blobs.BLOB_WINK))
        if destination not in player.map.nearby:
            raise utils.NotNearby(player.map, destination)
        time = player.map.calculate_travel_to(destination)
        if time > 2.0:
            if not await ctx.warn("{} It's a long trip, are you sure you want to go?".format(blobs.BLOB_THINK)):
                return
        # noinspection PyTypeChecker
        await player.travel_to(destination)
        await ctx.send("{} {} is now travelling to {} and will arrive in {:.1f} hours.".format(
            blobs.BLOB_SALUTE, player.name, destination.name, time))

    @commands.command(ignore_extra=False)
    async def explore(self, ctx):
        player = self.get_player(ctx.author._user)
        if not player:
            return await ctx.send("You don't have a player! {} Create one with `{}create`!".format(blobs.BLOB_PLSNO,
                                                                                                   ctx.prefix))
        time = player.map.calculate_explore()
        if time > 2.0:
            if not await ctx.warn("{} It'll take a while, are you sure?".format(blobs.BLOB_THINK)):
                return
        await player.explore()
        await ctx.send("{} {} is now exploring {} and will finish in {:.1f} hours.".format(
            blobs.BLOB_SALUTE, player.name, player.map.name, time))

    @commands.command(ignore_extra=False)
    async def status(self, ctx):
        player = self.get_player(ctx.author._user)
        if not player:
            return await ctx.send("You don't have a player! {} Create one with `{}create`!".format(blobs.BLOB_PLSNO,
                                                                                                   ctx.prefix))
        time = await player.travel_time()
        if time > 0:
            hours, ex = divmod(time, 3600)
            minutes, seconds = divmod(ex, 60)
            return await ctx.send("{} {} is currently travelling to {} and will finish"
                                  " in {} hours, {} minutes and {} seconds."
                                  .format(blobs.BLOB_PEEK, player, player._next_map, hours, minutes, seconds))
        time = await player.explore_time()
        if time > 0:
            hours, ex = divmod(time, 3600)
            minutes, seconds = divmod(ex, 60)
            return await ctx.send("{} {} is currently exploring {} and will finish"
                                  " in {} hours, {} minutes and {} seconds."
                                  .format(blobs.BLOB_PEEK, player, player.map, hours, minutes, seconds))
        await ctx.send("{} {} is currently idling. Try exploring or travelling!".format(blobs.BLOB_PEEK, player))

    @commands.command()
    async def profile(self, ctx: utils.EpicContext, *, member: discord.Member = None):
        member = member or ctx.author
        player = self.get_player(member._user)
        if not player:
            return await ctx.send("{} doesn't have a player {}".format(member, blobs.BLOB_PLSNO))
        embed = discord.Embed(color=discord.Colour.blurple(), description=f"Currently {player.status.name}")
        embed.set_author(name=str(member), icon_url=member.avatar_url_as(static_format="png", size=32))
        embed.add_field(name="Name", value=player.name)
        pl = self.get_player(ctx.author)
        if player.owner != ctx.author._user and (not pl or player.map not in pl.explored_maps):
            embed.add_field(name="Currently At", value="???")
        else:
            embed.add_field(name="Currently At", value=player.map)
        embed.add_field(name="Created At", value=player.created_at.strftime("%d/%m/%y @ %H:%M"), inline=False)
        await ctx.send(embed=embed)

    @commands.command(ignore_extra=False)
    async def rename(self, ctx):
        player = self.get_player(ctx.author._user)
        if not player:
            return await ctx.send("You don't have a player! {} Create one with `{}create`!".format(blobs.BLOB_PLSNO,
                                                                                                   ctx.prefix))

        def msgcheck(m):
            return m.author.id == ctx.author.id and len(m.content) < 33

        old_name = copy.copy(player.name)
        n = await ctx.send("{} What are you going to rename {} to?".format(blobs.BLOB_O, player))
        try:
            msg = await self.bot.wait_for('message', check=msgcheck, timeout=60.0)
        except asyncio.TimeoutError:
            await ctx.send("Took too long...")
        else:
            fmt = await commands.clean_content().convert(ctx, msg.content)
            player.name = fmt
            await player.save()
            await ctx.send("{} {} was renamed to {}".format(blobs.BLOB_THUMB, old_name, fmt))
        finally:
            await n.delete()

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
        for owner_id, name, map_id, created, explored in await self.fetch_players():
            try:
                user = self.bot.get_user(owner_id) or await self.bot.get_user_info(owner_id)
            except discord.NotFound:
                log.warning("Unresolved user id %s with player %s. Skipping initialization.", owner_id, name)
                continue
            status = await self.bot.redis.execute("GET", f"status_{user.id}")
            if status:
                status = utils.Status(int(status))
            else:
                status = utils.Status.idle
            player = utils.Player(**dict(
                owner=user,
                bot=self.bot,
                name=name,
                created_at=created,
                explored=list(map(self.bot.map_manager.get_map, explored)),
                status=status
            ))
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
