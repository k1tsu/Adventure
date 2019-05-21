# -> Builtin modules
import asyncio
import copy
import difflib
import io
import logging
import math
import operator
import random
import typing
from datetime import datetime

# -> Pip packages
import discord
import humanize
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

# -> Local files
import utils
import blobs

log = logging.getLogger("Adventure.PlayerManager")


class PlayerManager(commands.Cog, name="Players"):
    """Manages and handles everything to do with the Player."""
    def __init__(self, bot):
        self.bot = bot
        self.players = list()
        self.unload_event = asyncio.Event()
        self.bot.unload_complete.append(self.unload_event)
        self.is_creating = []
        with open("assets/profile_background.png", "rb") as f:
            thing = io.BytesIO(f.read())
            self.background = Image.open(thing)
            self.background.convert("RGBA")
        self._font = "assets/Inkfree.ttf"
        self.ignored_channels = []
        self.ignored_guilds = []
        self._player_flush_task = self.bot.loop.create_task(self.flush_players())

    def font(self, size=35):
        return ImageFont.truetype(self._font, size)

    def __repr__(self):
        return "<PlayerManager total: {0}>".format(len(self.players))

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if not ctx.guild:
            return
        if ctx.channel.id in self.ignored_channels or ctx.guild.id in self.ignored_guilds:
            return
        player = self.get_player(ctx.author)
        if not player:
            return
        try:
            await player.update(ctx)
        except TypeError:
            pass

    # -- Commands -- #

    @commands.command(ignore_extra=False)
    async def create(self, ctx):
        """Create a new player!
        You can't create one if you already have one.
        Use the "delete" command for that."""
        if ctx.author.id in self.is_creating:
            return
        player = self.get_player(ctx.author)
        if player:
            return await ctx.send("{} You already own \"{}\"!".format(blobs.BLOB_ANGERY, player))
        if await self.bot.db.fetchval("SELECT owner_id FROM players WHERE owner_id=$1;", ctx.author.id):
            return await ctx.send(f"You do have a player, just it has not been loaded.\n"
                                  f"Try using `{ctx.prefix}recover` to forcibly reload it.")
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
            player = utils.Player(owner=ctx.author, name=msg, bot=self.bot, created_at=datetime.utcnow())
            await player.save()
            self.players.append(player)
            await ctx.send("{} Success! \"{}\" was sent to map #0 (Abel).".format(blobs.BLOB_PARTY, msg))
        finally:
            self.is_creating.remove(ctx.author.id)

    @commands.command(ignore_extra=False)
    async def delete(self, ctx):
        """Begins the player deletion process.

        Pls no use <:pinkblobplsno:511668250313097246>"""
        player = self.get_player(ctx.author)
        if not player:
            raise utils.NoPlayer
        if await ctx.warn("Are you sure you want to delete \"{}\"? {}".format(player, blobs.BLOB_PLSNO)):
            await player.delete()
            await ctx.send("Goodbye, {}. {}".format(player, blobs.BLOB_SALUTE))

    @commands.command()
    async def travel(self, ctx, *, destination: str):
        """Travel to another area.
        Use the "maps" command to view nearby areas.
        You must own a player to use this."""
        player = self.get_player(ctx.author)
        if not player:
            raise utils.NoPlayer
        _map = self.bot.map_manager.resolve_map(destination)
        if not _map:
            close = difflib.get_close_matches(destination, list(map(operator.attrgetter("name"),
                                                                    self.bot.map_manager.maps)))
            if not close:
                return await ctx.send("Unknown map. Use `{}maps` to view the available maps.".format(ctx.prefix))
            return await ctx.send(f"Unknown map. Closest matches were: {'`' + '`, `'.join(close) + '`'}")
        if _map.id in (-1, 696969):
            return await ctx.send("Unknown map {}".format(blobs.BLOB_WINK))
        if _map not in player.map.nearby:
            raise utils.NotNearby(player.map, _map)
        time = _map.calculate_travel_to(player)
        if time > 2.0:
            if not await ctx.warn("{} It's a long trip, are you sure you want to go?".format(blobs.BLOB_THINK)):
                return
        # noinspection PyTypeChecker
        await player.travel_to(_map)
        await ctx.send("{} {} is now travelling to {} and will arrive in {:.0f} minutes.".format(
            blobs.BLOB_SALUTE, player.name, _map.name, time*60))

    @commands.command(ignore_extra=False)
    async def explore(self, ctx):
        """Explore the area around you.
        This will let you record what this area is and what can be found in it.
        More to come in this command soontm."""
        player = self.get_player(ctx.author)
        if not player:
            raise utils.NoPlayer
        if player.map.is_safe:
            return await ctx.send(f"{blobs.BLOB_ARMSCROSSED} {player.map} is already explored!")
        time = player.map.calculate_explore()
        if time > 2.0:
            if not await ctx.warn("{} It'll take a while, are you sure?".format(blobs.BLOB_THINK)):
                return
        await player.explore()
        await ctx.send("{} {} is now exploring {} and will finish in {:.0f} minutes.".format(
            blobs.BLOB_SALUTE, player.name, player.map.name, time*60))

    @commands.command(ignore_extra=False, aliases=['s'])
    async def status(self, ctx):
        """View your current players status.
        They can be idling, exploring, or travelling."""
        player = self.get_player(ctx.author)
        if not player:
            raise utils.NoPlayer
        time = await player.travel_time()
        if time > 0:
            hours, ex = divmod(time, 3600)
            minutes, seconds = divmod(ex, 60)
            return await ctx.send("{} {} is currently travelling to {} and will finish"
                                  " in {} hours, {} minutes and {} seconds."
                                  .format(blobs.BLOB_PEEK, player, player.next_map, hours, minutes, seconds))
        time = await player.explore_time()
        if time > 0:
            hours, ex = divmod(time, 3600)
            minutes, seconds = divmod(ex, 60)
            return await ctx.send("{} {} is currently exploring {} and will finish"
                                  " in {} hours, {} minutes and {} seconds."
                                  .format(blobs.BLOB_PEEK, player, player.map, hours, minutes, seconds))
        await ctx.send("{} {} is currently idling at {}. Try exploring or travelling!".format(
                       blobs.BLOB_PEEK, player, player.map))

    @commands.command(ignore_extra=False)
    async def rename(self, ctx):
        """Rename your player.
        The same rules apply, the name can only be 32 characters or less."""
        player = self.get_player(ctx.author)
        if not player:
            raise utils.NoPlayer

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

    @commands.command(aliases=['g'])
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def give(self, ctx, user: discord.User, amount: int):
        """Allows you to give money to another player."""
        player = self.get_player(ctx.author)
        if not player:
            raise utils.NoPlayer
        transfer = self.get_player(user)
        if not transfer:
            return await ctx.send(f"{blobs.BLOB_PLSNO} {user} does not have a player!")
        if amount > player.gold:
            return await ctx.send(f"{blobs.BLOB_ARMSCROSSED} You don't have enough gold for this action!")
        if amount < 0:
            return await ctx.send(f"{blobs.BLOB_WINK} You cannot give an negative amount to a player")
        player.gold -= amount
        transfer.gold += amount
        await ctx.send(f"{blobs.BLOB_O} {transfer} was given {amount} G!")

    @commands.command(aliases=['p'])
    @commands.cooldown(2, 30, commands.BucketType.user)
    async def profile(self, ctx, *, member: typing.Union[discord.Member, discord.User] = None):
        """Generates a profile for the member you specify, or yourself if omitted.

        This is a picture, so the cooldown is to prevent mass spam."""
        member = member or ctx.author
        player = self.get_player(member)
        if not player:
            ctx.command.reset_cooldown(ctx)
            if member == ctx.author:
                raise utils.NoPlayer
            return await ctx.send(f"{member} Doesn't have a player! {blobs.BLOB_PLSNO}")
        nx_player = self.get_player(ctx.author)
        if nx_player and (not nx_player.has_explored(player.map) and not player.map.is_safe):
            hide = True
        else:
            hide = False
        await ctx.trigger_typing()
        async with self.bot.session.get(str(member.avatar_url_as(format="png", size=256))) as get:
            n = io.BytesIO(await get.read())
        url = await self.bot.db.fetchval("SELECT cstmbg FROM supporters WHERE userid=$1;", member.id)
        if url:
            async with self.bot.session.get(url) as get:
                bg = io.BytesIO(await get.read())
        else:
            bg = None
        colour = await self.bot.db.fetchval("SELECT textcol FROM supporters WHERE userid=$1;", member.id)
        if colour is not None:
            colour = discord.Colour(colour)
        else:
            colour = discord.Colour.from_rgb(255, 255, 255)
        profile = await self.profile_for(n, player, hide=hide, custombg=bg, colour=colour)
        f = discord.File(profile, filename="profile.png")
        await ctx.send(file=f)

    @commands.command(ignore_extra=False)
    async def daily(self, ctx):
        """Claims your daily reward.

        This doesn't reset when the bot reboots, so don't even try :^)"""
        player = self.get_player(ctx.author)
        if not player:
            raise utils.NoPlayer
        ttl = await self.bot.redis.ttl(f"daily_{ctx.author.id}")
        if ttl < 0:
            if player.level < 2:
                await ctx.send(f"~~You probably won't gain any exp heads up.~~ {blobs.BLOB_INJURED}")
            gain = math.ceil(random.uniform(player.exp_to_next_level() / 4, player.exp_to_next_level() / 2))
            player.exp += gain
            await ctx.send(f"{blobs.BLOB_THUMB} You collected your daily reward and gained **{gain}** Experience!\n"
                           "Did you know that you can vote for more free rewards? See `*info` for the vote link!")
            await self.bot.redis.set(f"daily_{ctx.author.id}", "12", expire=86400)
        else:
            hours, ex = divmod(ttl, 3600)
            minutes, seconds = divmod(ex, 60)
            await ctx.send(f"{blobs.BLOB_ARMSCROSSED} "
                           f"The daily will reset in {hours} hours. {minutes} minutes and {seconds} seconds.")

    @commands.command(aliases=['sp'], ignore_extra=False)
    @commands.cooldown(2, 3600, commands.BucketType.user)
    async def speedup(self, ctx):
        """Pay some cash to speed up your travel/exploration.
        This is quite expensive, so make sure you collected a lot of money."""
        player = self.get_player(ctx.author)

        if not player:
            raise utils.NoPlayer
        if await player.is_travelling():
            cost = await player.travel_time()
        elif await player.is_exploring():
            cost = await player.explore_time()
        else:
            return await ctx.send(f"{blobs.BLOB_ARMSCROSSED} You aren't doing anything to speed up!")

        total = cost * 100

        if player.gold < cost:
            return await ctx.send(f"{blobs.BLOB_ARMSCROSSED} This costs {total:,} G, but you only have {player.gold:,} G!")

        if await ctx.warn(f"{blobs.BLOB_THINK} This will cost {total:,} G, are you sure?"):
            player.gold -= total
            await ctx.invoke(self.bot.get_command("modspeedup"), member=ctx.author, ignore_reaction=True)
            await ctx.send(f"{blobs.BLOB_THUMB} Done! Try sending a message.")

    @commands.group(aliases=['lb'], invoke_without_command=True)
    async def leaderboard(self, ctx, count: int = 20):
        """Views the top 20 players in your server.
        Try to reach the top of the leaderboard!"""
        headers = ["Name", "Owner", "Level", "Total Caught"]
        table = utils.TabularData()
        table.set_columns(headers)
        table.add_rows([[p.name, str(p.owner), p.level, sum(p.raw_compendium_data)]
                        for p in sorted(
                filter(lambda m: m.owner in ctx.guild.members and m.owner.id != 455289384187592704, self.players),
                key=lambda m: sum(m.raw_compendium_data), reverse=True)][:count])
        try:
            await ctx.send(f"```\n{table.render()}\n```")
        except discord.HTTPException:
            await ctx.send("Count too large.")

    @leaderboard.command(ignore_extra=False, name="global", aliases=['g'])
    async def _global(self, ctx, count: int = 20):
        """Same as the regular command, but shows the global leaderboard."""
        headers = ["Name", "Owner", "Level", "Total Caught"]
        table = utils.TabularData()
        table.set_columns(headers)
        table.add_rows([[p.name, str(p.owner), p.level, sum(p.raw_compendium_data)]
                        for p in sorted(self.players, key=lambda m: sum(m.raw_compendium_data), reverse=True)
                        if p.owner.id != 455289384187592704][:count])
        try:
            await ctx.send(f"```\n{table.render()}\n```")
        except discord.HTTPException:
            await ctx.send("Count too large.")

    @leaderboard.command(ignore_extra=False, aliases=['xp'])
    async def experience(self, ctx, count: int = 20):
        """Same as the regular command, but sorted by Experience points."""
        headers = ["Name", "Owner", "Experience", "Level"]
        table = utils.TabularData()
        table.set_columns(headers)
        table.add_rows([[p.name, str(p.owner), p.exp, p.level]
                        for p in sorted(self.players, key=lambda m: m.exp, reverse=True)
                        if p.owner.id != 455289384187592704][:count])
        try:
            await ctx.send(f"```\n{table.render()}```")
        except discord.HTTPException:
            await ctx.send("Count too large.")

    @commands.command(ignore_extra=False, aliases=['cp', 'comp'])
    async def compendium(self, ctx):
        """Views all the enemies you have captured."""
        player = self.get_player(ctx.author)
        if not player:
            raise utils.NoPlayer
        await ctx.send(f"```\n{player.compendium.format()}\n```")

    # -- Player Manager stuff -- #

    def fetch_players(self):
        return self.bot.db.fetch("SELECT * FROM players;")

    def get_player(self, user: typing.Union[discord.Member, discord.User]) -> typing.Optional[utils.Player]:
        return discord.utils.get(self.players, owner=user)

    @utils.async_executor()
    def profile_for(self, avatar: io.BytesIO, player: utils.Player, hide: bool = False, *, custombg: io.BytesIO = None,
                    colour: discord.Colour = None):
        image = Image.open(avatar).convert("RGBA")
        image = image.resize((256, 256))
        if not custombg:
            background = self.background.copy()
        else:
            background = Image.open(custombg).convert("RGBA")
        colour = colour.to_rgb() if colour else (255, 255, 255)
        background.paste(image, (0, 0), image)
        draw = ImageDraw.Draw(background)
        created = humanize.naturaltime(player.created_at)
        draw.text((5, 255), f"{player.name}\n{player.owner}\nCreated {created}", colour,
                  self.font())
        draw.text((265, 0), f"Tier {player.level}\n{player.exp} EXP", colour,
                  self.font())
        if player.status is utils.Status.idle:
            status = "Idling at"
            pmap = str(player.map) if not hide else "???"
        elif player.status is utils.Status.travelling:
            status = "Travelling to"
            pmap = str(player.next_map) if not hide else "???"
        elif player.status is utils.Status.exploring:
            status = "Exploring"
            pmap = str(player.map) if not hide else "???"
        else:
            status = "???"
            pmap = str(player.map) if not hide else "???"
        draw.text((265, 125), f"{status}\n{pmap}", colour,
                  self.font())
        draw.text((265, 205), f"{player.gold:,} G", colour,
                  self.font())
        n = io.BytesIO()
        background.save(n, "png")
        n.seek(0)
        return n

    async def flush_players(self):
        await self.bot.prepared.wait()
        while await asyncio.sleep(3600, True):
            async with self.bot.db.acquire() as cursor:
                for p in self.players:
                    await p.save(cursor=cursor)
            log.info("Flushed players.")

    # -- Events -- #

    def cog_unload(self):
        try:
            self._player_flush_task.cancel()
        except asyncio.CancelledError:
            pass
        self.bot.unload_complete.remove(self.unload_event)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.prepared.wait()
        if len(self.players) > 0:
            return
        # log.debug("INIT")
        self.ignored_channels = list(map(int, await self.bot.redis.smembers("channel_ignore")))
        self.ignored_guilds = list(map(int, await self.bot.redis.smembers("guild_ignore")))
        for data in await self.fetch_players():
            owner_id, name, map_id, created, explored, exp, compendium, gold, *_ = data
            # log.debug("DATA %s", data)
            user = self.bot.get_user(owner_id)
            if not user:
                log.warning("Unknown user id %s. Skipping initialization. (%s)", owner_id, len(self.bot.users))
                continue
            status = await self.bot.redis.get(f"status_{user.id}")
            if status:
                status = utils.Status(int(status))
            else:
                status = utils.Status.idle
            player = utils.Player(
                owner=user,
                bot=self.bot,
                name=name,
                created_at=created,
                explored=list(map(self.bot.map_manager.get_map, explored)),
                status=status,
                exp=exp,
                next_map=await self.bot.redis.get(f"next_map_{user.id}"),
                compendium=compendium,
                gold=gold
            )
            player.map = map_id
            self.players.append(player)
            log.info("Player \"%s\" (%s) initialized at map \"%s\".", player.name, str(player.owner), player.map)

    @commands.Cog.listener()
    async def on_logout(self):
        log.debug("LOGOUT WAS CALLED")
        async with self.bot.db.acquire() as cur:
            for player in self.players:
                await player.save(cursor=cur)
                log.info("Flushed player \"%s\" (%s).", player.name, player.owner)
        self.unload_event.set()


def setup(bot):
    cog = PlayerManager(bot)
    bot.add_cog(cog)
    # bot.player_manager = cog

