# -> Builtin modules
import collections
import inspect
import os
import pathlib
import random
import time
import typing

# -> Pip packages
import discord
import jishaku
from discord.ext import commands


class Misc(commands.Cog, name="Miscellaneous"):
    """Miscellaneous commands are found here.
    Includes source and pinging."""
    def __init__(self, bot):
        self.bot = bot
        self.valid = ("py", "sql", "md", "txt", "json")

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

    @commands.command()
    async def epic(self, ctx):
        """Try to find the most epic message."""
        await ctx.trigger_typing()
        messages = await ctx.history().filter(
            lambda m: not m.content.startswith("*") and "epic" in m.content.lower() and not m.author.bot
        ).flatten()
        if not messages:
            return await ctx.send("Not epic.")
        await ctx.send(random.choice(messages).jump_url)

    @commands.command(hidden=True)
    async def git(self, ctx):
        async for message in self.bot.get_channel(544405638349062155).history(limit=10).filter(
            lambda m: len(m.embeds) > 0 and m.author.discriminator == "0000"
        ):
            return await ctx.send(embed=message.embeds[0])
        await ctx.send("blank")
        # ideally shouldnt happen

    @commands.command()
    async def avatar(self, ctx, *, member: typing.Union[discord.Member, discord.User] = None):
        """Views your, or someone elses avatar."""
        member = member or ctx.author
        embed = discord.Embed(color=discord.Colour.blurple())
        embed.set_author(name=str(member), icon_url=member.avatar_url_as(format="png", size=32))
        embed.set_image(url=member.avatar_url_as(static_format="png"))
        await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        """Check my connection time with Discord."""
        start = time.perf_counter()
        await ctx.author.trigger_typing()
        end = time.perf_counter()
        ms = round((end-start)*1000)
        await ctx.send(f":ping_pong: **{ms}**ms")

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

        if module.startswith(self.__module__.split(".")[0]):
            location = os.path.relpath(inspect.getfile(src)).replace('\\', '/')
            source += "/blob/master"

        elif module.startswith("jishaku"):
            source = f"https://github.com/Gorialis/jishaku/blob/{jishaku.__version__}"
            location = module.replace(".", "/") + ".py"

        else:
            raise RuntimeError("*source")

        final = f"<{source}/{location}#L{first}-L{first + len(lines) - 1}>"
        await ctx.send(final)

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

    @commands.command(hidden=True)
    async def todo(self, ctx):
        await ctx.send("`todo list`")

    @commands.command(hidden=True)
    async def levels(self, ctx):
        await ctx.send([(x, x**3) for x in range(1, 101)])


def setup(bot):
    bot.add_cog(Misc(bot))
