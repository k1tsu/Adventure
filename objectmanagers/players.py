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
import uuid
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


class PlayerManager(commands.Cog, name="Player Manager"):
    """Manages and handles everything to do with the Player."""
    def __init__(self, bot):
        self.bot = bot
        self.players = list()
        self.unload_event = asyncio.Event()
        self.bot.unload_complete.append(self.unload_event)
        self.is_creating = []
        self.is_fighting = {}  # dict of {(player, player): uuid4}
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

    @commands.command(ignore_extra=False)
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

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def profile(self, ctx, *, member: discord.Member = None):
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
        async with self.bot.session.get(member.avatar_url_as(format="png", size=256)) as get:
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
        if player.level < 2:
            await ctx.send(f"~~You probably won't gain any exp heads up.~~ {blobs.BLOB_INJURED}")
        ttl = await self.bot.redis("TTL", f"daily_{ctx.author.id}")
        if ttl < 0:
            gain = math.ceil(random.uniform(player.exp_to_next_level() / 4, player.exp_to_next_level() / 2))
            player.exp += gain
            await ctx.send(f"{blobs.BLOB_THUMB} You collected your daily reward and gained **{gain}** Experience!\n"
                           "Did you know that you can vote for more free rewards? See `*info` for the vote link!")
            await self.bot.redis("SET", f"daily_{ctx.author.id}", "12", "EX", "86400")
        else:
            hours, ex = divmod(ttl, 3600)
            minutes, seconds = divmod(ex, 60)
            await ctx.send(f"{blobs.BLOB_ARMSCROSSED} "
                           f"The daily will reset in {hours} hours. {minutes} minutes and {seconds} seconds.")

    @commands.command(ignore_extra=False, aliases=['lb'])
    async def leaderboard(self, ctx):
        """Views the top 10 most experienced players.
        Try to reach the top of the tower <:pinkblobwink:544628885023621126>"""
        headers = ["Name", "Owner", "EXP", "Level"]
        table = utils.TabularData()
        table.set_columns(headers)
        table.add_rows([[p.name, str(p.owner), p.exp, p.level] for p in sorted(
            filter(lambda m: m.exp > 0, self.players), key=lambda m: m.exp, reverse=True)][:10])
        await ctx.send(f"```\n{table.render()}\n```")

    @commands.command(ignore_extra=False, aliases=['cp', 'comp'])
    async def compendium(self, ctx):
        """Views all the enemies you have currently seen."""
        player = self.get_player(ctx.author)
        if not player:
            raise utils.NoPlayer
        await ctx.send(f"```\n{player.compendium.format()}\n```")

    @commands.command()
    @commands.cooldown(10, 600, commands.BucketType.user)
    async def fight(self, ctx, *, member: discord.Member):
        """Fight your friends in a battle to the death!
        Not actually to the death, but the winner gets a shit load of EXP."""
        if ctx.author == member:
            self.is_fighting.pop(ctx.author.id)
            return await ctx.send(f"You can't fight yourself! {blobs.BLOB_INJURED}")

        alpha = self.bot.player_manager.get_player(ctx.author)
        if not alpha:
            self.is_fighting.pop(ctx.author.id)
            self.is_fighting.pop(member.id)
            raise utils.NoPlayer

        beta = self.bot.player_manager.get_player(member)
        if not beta:
            self.is_fighting.pop(ctx.author.id)
            self.is_fighting.pop(member.id)
            return await ctx.send(f"{member} does not have a player! {blobs.BLOB_PLSNO}")

        if alpha.level < 1:
            self.is_fighting.pop(ctx.author.id)
            self.is_fighting.pop(member.id)
            return await ctx.send(f"You aren't a high enough level to fight! {blobs.BLOB_ARMSCROSSED}")

        if beta.level < 1:
            self.is_fighting.pop(ctx.author.id)
            self.is_fighting.pop(member.id)
            return await ctx.send(f"{member} isn't a high enough level to fight! {blobs.BLOB_ARMSCROSSED}")

        if not await ctx.warn(f"{member}, do you wish to fight {ctx.author}?", waiter=member):
            self.is_fighting.pop(ctx.author.id)
            self.is_fighting.pop(member.id)
            return await ctx.send(f"{member} did not want to fight...")

        ahp = copy.copy(alpha.healthpoints)
        bhp = copy.copy(beta.healthpoints)
        chances = [*['a'] * alpha.level, *['b'] * beta.level, *['c'] * ((alpha.level + beta.level) // 2)]
        while not (ahp <= 0 or bhp <= 0):
            win = random.choice(chances)
            if win == 'a':
                hurt = random.randint(math.ceil(alpha.strength / 3), math.ceil(alpha.strength))
                bhp -= hurt
                await ctx.send(f"**{alpha.name}** damaged **{beta.name}** for **{hurt}** Hitpoints!"
                               f" {blobs.BLOB_INJURED}")
            elif win == 'b':
                hurt = random.randint(math.ceil(beta.strength / 3), math.ceil(beta.strength))
                ahp -= hurt
                await ctx.send(f"**{beta.name}** damaged **{alpha.name}** for **{hurt}** Hitpoints!"
                               f" {blobs.BLOB_INJURED}")
            else:
                await ctx.send(f"{blobs.BLOB_ANGERY} Nothing happened...")
            await asyncio.sleep(1)
        if ahp <= 0:
            exp = math.ceil(random.uniform(alpha.strength / 3, alpha.strength) / 2)
            beta.exp += exp
            await ctx.send(f"""**{alpha.name}** fainted! {blobs.BLOB_CHEER}
**{beta.name}** gained **{exp}** Experience Points!""")
        elif bhp <= 0:
            exp = math.ceil(random.uniform(beta.strength / 3, beta.strength))
            alpha.exp += exp
            await ctx.send(f"""**{beta.name}** fainted! {blobs.BLOB_CHEER}
**{alpha.name}** gained **{exp}** Experience Points!""")
        self.is_fighting.pop(ctx.author.id)
        self.is_fighting.pop(member.id)

    @fight.error
    async def fight_error(self, ctx, exc):
        if isinstance(exc, commands.NotOwner):
            return
        await self.bot.get_cog("Handler").on_command_error(ctx, exc, enf=True)

    @fight.before_invoke
    async def fight_before_invoke(self, ctx):
        alpha = ctx.args[-1].author
        beta = ctx.kwargs.get("member")
        battle_id = uuid.uuid4()
        if alpha.id in self.is_fighting:
            battle = self.is_fighting[alpha.id]
            if battle != battle_id:
                await ctx.send(f"You are already in a battle! {blobs.BLOB_ANGERY}")
                raise commands.NotOwner
        if beta.id in self.is_fighting:
            battle = self.is_fighting[beta.id]
            if battle != battle_id:
                await ctx.send(f"{beta} is already in a battle! {blobs.BLOB_ANGERY}")
                raise commands.NotOwner
        self.is_fighting[alpha.id] = battle_id
        self.is_fighting[beta.id] = battle_id

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
        self.ignored_channels = list(map(int, await self.bot.redis("SMEMBERS", "channel_ignore")))
        self.ignored_guilds = list(map(int, await self.bot.redis("SMEMBERS", "guild_ignore")))
        for data in await self.fetch_players():
            owner_id, name, map_id, created, explored, exp, compendium, gold, *_ = data
            user = self.bot.get_user(owner_id)
            if not user:
                log.warning("Unknown user id %s. Skipping initialization.", owner_id)
                continue
            status = await self.bot.redis("GET", f"status_{user.id}")
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
                next_map=await self.bot.redis("GET", f"next_map_{user.id}"),
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
    bot.player_manager = cog


def teardown(bot):
    bot.player_manager = None
