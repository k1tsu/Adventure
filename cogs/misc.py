# -> Builtin modules
import collections
import inspect
import logging
import os
import pathlib
import random
import typing
from datetime import datetime

# -> Pip packages
import discord
import humanize
import jishaku
from discord.ext import commands

import blobs
import utils


log = logging.getLogger("Adventure.PlayerManager")


def perm_check(**perms):
    async def predicate(ctx):
        if ctx.author.id in ctx.bot.config.OWNERS:
            return True
        permissions = ctx.channel.permissions_for(ctx.author)
        invalid = []
        for p, v in perms.items():
            if not getattr(permissions, p, None) == v:
                invalid.append(p)
        if invalid:
            raise commands.MissingPermissions(invalid)
        return True
    return commands.check(predicate)


class Misc(commands.Cog):
    """Miscellaneous commands are found here.
    Includes source and pinging."""
    def __init__(self, bot):
        self.bot = bot
        self.valid = ("py", "sql", "md", "txt", "json")

    @commands.command(ignore_extra=False, aliases=['about'])
    async def info(self, ctx):
        """Views basic information about Adventure."""
        embed = discord.Embed(colour=discord.Colour(0xA8C16D), title="Info about Adventure",
                              description=f"Here is some basic information. For more, check out `{ctx.prefix}help`.")
        embed.set_author(name=str(self.bot.user), icon_url=str(self.bot.user.avatar_url_as(format="png", size=32)))
        stats = f"""Guilds: {len(self.bot.guilds)}
Members: {len(set(self.bot.get_all_members()))}
Memory Usage: {humanize.naturalsize(self.bot.process.memory_full_info().uss)}
Players: {len(self.bot.player_manager.players)}
Maps: {len(self.bot.map_manager.maps)}
Enemies: {len(self.bot.enemy_manager.enemies)}"""
        embed.add_field(name="Statistics", value=stats, inline=False)
        upt = humanize.naturaldelta(datetime.utcnow() - self.bot.init)
        embed.add_field(name="Uptime", value=upt, inline=False)
        links = ("[Invite](https://discordapp.com/api/oauth2/authorize?"
                 "client_id=482373088109920266&permissions=388160&scope=bot)\n"
                 "[DBL](https://discordbots.org/bot/482373088109920266) / "
                 "[Vote](https://discordbots.org/bot/482373088109920266/vote)\n"
                 "[Source](https://github.com/XuaTheGrate/Adventure)\n"
                 "[Support](https://discord.gg/hkweDCD)\n"
                 "[Donate](https://www.patreon.com/xua_yraili)")
        embed.add_field(name="Links", value=links)
        embed.set_footer(text="Created by Xua#4427")
        await ctx.send(embed=embed)

    @commands.command(aliases=['loc'], hidden=True)
    @commands.is_owner()
    async def linecount(self, ctx):
        total = collections.Counter()
        for path, subdirs, files in os.walk("."):
            for name in files:
                ext = name.split(".")[-1]
                if ext not in self.valid:
                    continue
                if 'venv' in './' + str(pathlib.PurePath(path, name)):
                    continue
                with open('./' + str(pathlib.PurePath(path, name)), 'r', encoding='utf-8') as f:
                    for l in f:
                        if (l.strip().startswith("#") and ext == 'py') or len(l.strip()) == 0:
                            continue
                        total[ext] += 1
        t = {a: b for a, b in sorted(total.items(), key=lambda x: x[1], reverse=True)}
        sizea = max(len(str(x)) for x in t.values())
        sizeb = max(len(str(x)) for x in t.keys())
        fmt = "```\n" + "\n".join(sorted([f"{f'{x:>{sizea}} lines of {y:>{sizeb}} code'}" for y, x in t.items()],
                                         key=lambda m: len(m))) + "```"
        await ctx.send(fmt)

    @commands.command(ignore_extra=False)
    async def epic(self, ctx):
        """Try to find the most epic message."""
        await ctx.trigger_typing()
        messages = await ctx.history().filter(
            lambda m: not m.content.startswith("*") and "epic" in m.content.lower() and not m.author.bot
        ).flatten()
        if not messages:
            return await ctx.send("Not epic.")
        await ctx.send(random.choice(messages).jump_url)

    @commands.command(hidden=True, ignore_extra=False)
    async def git(self, ctx):
        async for message in self.bot.get_channel(561394007238770688).history(limit=10).filter(
            lambda m: len(m.embeds) > 0 and m.author.discriminator == "0000"
        ):
            return await ctx.send(embed=message.embeds[0])
        await ctx.send("blank")
        # ideally shouldnt happen

    @commands.command()
    async def avatar(self, ctx, *, member: typing.Union[discord.Member, discord.User] = None):
        """Views your, or someone elses avatar."""
        member = member or ctx.author
        embed = discord.Embed(color=discord.Colour(11059565))
        embed.set_author(name=str(member), icon_url=str(member.avatar_url_as(format="png", size=32)))
        embed.set_image(url=str(member.avatar_url_as(static_format="png")))
        await ctx.send(embed=embed)

    @commands.command(ignore_extra=False)
    async def ping(self, ctx):
        """Check my connection time with Discord."""
        await ctx.send(f":ping_pong: **{self.bot.latency*1000:.0f}**ms")

    @commands.command()
    async def say(self, ctx, *, message: commands.clean_content):
        """Repeats the message you say."""
        await ctx.send(message)

    @commands.command()
    async def source(self, ctx, *, command=None):
        """View the source code for my bot.
        Can also find the source for specific commands."""
        source = "https://github.com/XuaTheGrate/Adventure"
        if not command:
            return await ctx.send(source)

        cmd = self.bot.get_command(command.replace(".", " "))
        if not cmd:
            return await ctx.send("Couldn't find that command.")

        src = cmd.callback
        lines, first = inspect.getsourcelines(src)
        module = inspect.getmodule(src).__name__

        if module.startswith("jishaku"):
            source = f"https://github.com/Gorialis/jishaku/blob/{jishaku.__version__}"
            location = module.replace(".", "/") + ".py"

        else:
            location = os.path.relpath(inspect.getfile(src)).replace('\\', '/')
            source += "/blob/master"

        final = f"<{source}/{location}#L{first}-L{first + len(lines) - 1}>"
        await ctx.send(final)

    @commands.command(ignore_extra=False)
    async def tip(self, ctx):
        """Gives you a random hint about something."""
        hint, id = await self.bot.db.fetchrow("SELECT * FROM tips ORDER BY random() LIMIT 1;")
        await ctx.send(f"#{id}. {hint}")

    @commands.command(ignore_extra=False)
    async def invite(self, ctx):
        """Generates an invite URL to invite me to your server.

        Two options:
        \u200b\tThe first: comes with all the recommended permissions.
        \u200b\tThe second: minimal (0) permissions."""
        embed = discord.Embed(title="Here's my invite links!", color=discord.Color.blurple())
        embed.description = ("[The full experience]"
                             "(https://discordapp.com/api/oauth2/authorize"
                             "?client_id=482373088109920266&permissions=388160&scope=bot)\n"
                             "[Minimalistic setup]"
                             "(https://discordapp.com/api/oauth2/authorize"
                             "?client_id=482373088109920266&permissions=0&scope=bot)")
        await ctx.send(embed=embed)

    @commands.command(ignore_extra=False)
    async def support(self, ctx):
        """Gives you the Instant Invite to Adventure!'s support server."""
        await ctx.send(f"You can join the support server via this invite: https://discord.gg/hkweDCD")

    @commands.command(hidden=True, ignore_extra=False)
    async def todo(self, ctx):
        await ctx.send("`todo list`")

    @commands.command(hidden=True, ignore_extra=False)
    async def levels(self, ctx):
        await ctx.send([(x, x**3) for x in range(1, 101)])

    @commands.group(hidden=True, invoke_without_command=True, ignore_extra=False)
    @perm_check(manage_guild=True)
    async def prefix(self, ctx):
        await ctx.send("\n".join(self.bot.prefixes[ctx.guild.id]))

    @prefix.command()
    @perm_check(manage_guild=True)
    async def add(self, ctx, *prefixes):
        self.bot.prefixes[ctx.guild.id] |= set(prefixes)
        await ctx.add_reaction(blobs.BLOB_TICK)

    @prefix.command()
    @perm_check(manage_guild=True)
    async def remove(self, ctx, *prefixes):
        for prefix in prefixes:
            self.bot.prefixes[ctx.guild.id].remove(prefix)
        await ctx.add_reaction(blobs.BLOB_TICK)

    @prefix.error
    @add.error
    @remove.error
    async def handler(self, ctx, exc):
        if not isinstance(exc, commands.CommandInvokeError):
            return
        await ctx.author.send(f"```py\n{utils.format_exception(exc.original)}\n```")
        await ctx.add_reaction(blobs.BLOB_CROSS)

    @commands.command()
    async def vote(self, ctx):
        """Gives you the DBL voting link."""
        await ctx.send("You can vote for Adventure! by using this link!\n"
                       "<https://discordbots.org/bot/482373088109920266/vote>")

    @commands.command()
    async def patreon(self, ctx):
        """Gives you the Patreon link to support me.
        If you do donate to me, please contact me and I'll arrange adding you to the supporters list."""
        if await self.bot.db.fetchval("SELECT userid FROM supporters WHERE userid=$1;", ctx.author.id):
            return await ctx.send("Thank you for donating! If you don't have access to the supporter only functions,"
                                  " please contact me (Xua#4427) and I will fix it.")
        await ctx.send("I've set up a Patreon! You can donate to me via this link: <https://www.patreon.com/xua_yraili>"
                       "\nIf you do donate, please contact me (Xua#4427) and I'll add you to my supporters.")

    @commands.command(hidden=True, ignore_extra=False)
    async def recover(self, ctx):
        """Attempts to re-cache your player, if it isn't.
        You will be alerted to use this if you do have a player, but it hasn't been loaded."""
        pm = self.bot.player_manager
        if pm.get_player(ctx.author):
            return await ctx.send(f"{blobs.BLOB_ANGERY} Your player is already cached!")
        data = await self.bot.db.fetchrow("SELECT * FROM players WHERE owner_id=$1;", ctx.author.id)
        if not data:
            return await ctx.send(f"{blobs.BLOB_SAD} Couldn't find any data for you."
                                  f"\nIf you did have a player, then I'm afraid it's gone now.")
        owner_id, name, map_id, created, explored, exp, compendium, gold, *_ = data
        user = self.bot.get_user(owner_id)
        status = await self.bot.redis("GET", f"status_{owner_id}")
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
        pm.players.append(player)
        log.info("Recovered player %s (%s).", player.name, ctx.author)
        await ctx.send(f"{blobs.BLOB_PARTY} Success! {player.name} has been revived!")

    @staticmethod
    def advanced_strat(bot):
        def inner(message):
            return message.content.startswith('*') or message.author == bot.user
        return inner

    @staticmethod
    def basic_strat(bot):
        def inner(message):
            return message.author == bot.user
        return inner

    @commands.command()
    async def cleanup(self, ctx):
        if not ctx.guild:
            async for message in ctx.history(limit=50):
                if message.author == self.bot.user:
                    await message.delete()
        else:
            if ctx.guild.me.guild_permissions.manage_messages:
                strat = self.advanced_strat(self.bot)
            else:
                strat = self.basic_strat(self.bot)
            await ctx.channel.purge(limit=50, check=strat, bulk=ctx.guild.me.guild_permissions.manage_messages)


def setup(bot):
    bot.add_cog(Misc(bot))
