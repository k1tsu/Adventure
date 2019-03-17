# -> Builtin modules
import asyncio
import copy
import io
import logging
import random
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


class MapConverter(commands.Converter):
    async def convert(self, ctx, argument):
        return ctx.bot.map_manager.resolve_map(argument)


class PlayerManager(commands.Cog, name="Player Manager"):
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
        self._font = "assets/segoesc.ttf"

    def font(self, size=32):
        return ImageFont.truetype(self._font, size)

    def __repr__(self):
        return "<PlayerManager total: {0}>".format(len(self.players))

    @commands.Cog.listener()
    async def on_command(self, ctx):
        player = self.get_player(ctx.author)
        if not player:
            return
        await player.update(ctx)

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
        player = self.get_player(ctx.author)
        if not player:
            return await ctx.send("You don't have a player! {} Create one with `{}create`!".format(blobs.BLOB_PLSNO,
                                                                                                   ctx.prefix))
        if await ctx.warn("Are you sure you want to delete \"{}\"? {}".format(player, blobs.BLOB_PLSNO)):
            await player.delete()
            await ctx.send("Goodbye, {}. {}".format(player, blobs.BLOB_SALUTE))

    @commands.command()
    async def travel(self, ctx, *, destination: MapConverter):
        """Travel to another area.
        Use the "maps" command to view nearby areas.
        You must own a player to use this."""
        player = self.get_player(ctx.author)
        if not player:
            return await ctx.send("You don't have a player! %s Create one with `%screate`!" % (blobs.BLOB_PLSNO,
                                                                                               ctx.prefix))
        if not destination:
            return await ctx.send("Unknown map. Use `{}maps` to view the available maps.".format(ctx.prefix))
        if destination.id in (-1, 696969):
            return await ctx.send("Unknown map {}".format(blobs.BLOB_WINK))
        if destination not in player.map.nearby:
            raise utils.NotNearby(player.map, destination)
        time = destination.calculate_travel_to(player)
        if time > 2.0:
            if not await ctx.warn("{} It's a long trip, are you sure you want to go?".format(blobs.BLOB_THINK)):
                return
        # noinspection PyTypeChecker
        await player.travel_to(destination)
        await ctx.send("{} {} is now travelling to {} and will arrive in {:.1f} hours.".format(
            blobs.BLOB_SALUTE, player.name, destination.name, time))

    @commands.command(ignore_extra=False)
    async def explore(self, ctx):
        """Explore the area around you.
        This will let you record what this area is and what can be found in it.
        More to come in this command soontm."""
        player = self.get_player(ctx.author)
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
        """View your current players status.
        They can be idling, exploring, or travelling."""
        player = self.get_player(ctx.author)
        if not player:
            return await ctx.send("You don't have a player! {} Create one with `{}create`!".format(blobs.BLOB_PLSNO,
                                                                                                   ctx.prefix))
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

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def profile(self, ctx, *, member: discord.Member = None):
        member = member or ctx.author
        player = self.get_player(member)
        if not player:
            return await ctx.send("You don't have a player! {} Create one with `{}create`!".format(blobs.BLOB_PLSNO,
                                                                                                   ctx.prefix))
        await ctx.trigger_typing()
        async with self.bot.session.get(member.avatar_url_as(format="png", size=256)) as get:
            n = io.BytesIO(await get.read())
        profile = await self.profile_for(n, player)
        f = discord.File(profile, filename="profile.png")
        await ctx.send(file=f)

    @commands.command(ignore_extra=False)
    @commands.cooldown(2, 60, commands.BucketType.user)
    async def encounter(self, ctx):
        player = self.get_player(ctx.author)
        if not player:
            return await ctx.send("You don't have a player! {} Create one with `{}create`!".format(blobs.BLOB_PLSNO,
                                                                                                   ctx.prefix))
        if not player.has_explored(player.map):
            return await ctx.send("{} You must explore the current map first!".format(blobs.BLOB_ARMSCROSSED))
        if player.map.id == 0:
            return await ctx.send(f"{blobs.BLOB_ARMSCROSSED} There are no enemies in Abel!")
        enemies = self.bot.enemy_manager.enemies_for(player.map)
        if not enemies:
            log.debug("2.5")
            raise RuntimeError(f"No enemies were discovered for map {player.map!r}")
        strongest = max(enemies, key=lambda e: e.tier)
        chance = 100 + ((len(enemies) - strongest.tier) - player.level)
        # log.debug("ENCOUNTER CHANCE %s %s", ctx.author, chance)
        if random.randint(0, 100) < chance:
            enemy = random.choice(enemies)
            if enemy.tier > player.level:
                await ctx.send(f"{blobs.NOTLIKE_BLOB} You encountered a **{enemy.name}** but it's too powerful!"
                               f"\nYou ran away to avoid injury.")
            else:
                if enemy.defeat(player.level):
                    exp = random.randint(enemy.tier, enemy.tier ** 3)+1
                    await ctx.send(f"<pink blob cheer> You encountered a **{enemy.name}** and defeated it!\n"
                                   f"You gained **{exp}** experience points!")
                    # TODO: gain / lose gold on win / loss
                    player.exp += exp
                else:
                    player.map = 0
                    await ctx.send(f"{blobs.BLOB_INJURED} You encountered a **{enemy.name}** and failed to defeat it!\n"
                                   f"You were knocked out and magically sent back to Abel.")
        else:
            await ctx.send("{} You couldn't find anything.")

    # -- Player Manager stuff -- #

    def fetch_players(self):
        return self.bot.db.fetch("SELECT * FROM players;")

    def get_player(self, user: discord.User) -> utils.Player:
        return discord.utils.get(self.players, owner=user)

    @utils.async_executor()
    def profile_for(self, avatar: io.BytesIO, player: utils.Player):
        image = Image.open(avatar).convert("RGBA")
        background = self.background.copy()
        background.paste(image, (0, 0), image)
        draw = ImageDraw.Draw(background)
        draw.text((10, 245), player.name, (255, 255, 255),
                  self.font(50))
        draw.text((10, 320), str(player.owner), (255, 255, 255),
                  self.font(32))
        draw.text((265, 0), f"Tier {player.level}", (255, 255, 255),
                  self.font(64))
        draw.text((315, 70), f"{player.exp} EXP", (255, 255, 255),
                  self.font(), align="center")
        if player.status is utils.Status.idle:
            status = "Idling at"
            pmap = str(player.map)
        elif player.status is utils.Status.travelling:
            status = "Travelling to"
            pmap = str(player.next_map)
        elif player.status is utils.Status.exploring:
            status = "Exploring"
            pmap = str(player.map)
        else:
            status = "???"
            pmap = str(player.map)
        draw.text((240, 125), f"{status:^{len(status)+4}}\n{pmap:^{len(status)+4}}", (255, 255, 255),
                  self.font(), align="center")
        created = humanize.naturaltime(player.created_at)
        draw.text((260, 265), f"Created\n{created:^7}", (255, 255, 255),
                  self.font(), align="center")
        n = io.BytesIO()
        background.save(n, "png")
        n.seek(0)
        return n

    # -- Events -- #

    def cog_unload(self):
        self.bot.unload_complete.remove(self.unload_event)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.prepared.wait()
        if len(self.players) > 0:
            return
        for data in await self.fetch_players():
            owner_id, name, map_id, created, explored, exp, *_ = data
            try:
                user = self.bot.get_user(owner_id) or await self.bot.get_user_info(owner_id)
            except discord.NotFound:
                log.warning("Unresolved user id %s with player %s. Skipping initialization.", owner_id, name)
                continue
            status = await self.bot.redis("GET", f"status_{user.id}")
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
                status=status,
                exp=exp,
                next_map=await self.bot.redis("GET", f"next_map_{user.id}")
            ))
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
    bot.player_manager = cog


def teardown(bot):
    bot.player_manager = None
