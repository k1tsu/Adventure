from discord.ext import commands
import discord

import logging
log = logging.getLogger("Adventure.Help")


class Help:
    def __init__(self, bot):
        self.bot = bot

    def formatter(self, i, stack=1, ignore_hidden=False):
        for cmd in i:
            if cmd.hidden and not ignore_hidden:
                continue
            yield "\u200b " * (stack*2) + f"►{cmd}\n"
            if isinstance(cmd, commands.Group):
                yield from self.formatter(cmd.commands, stack+1)

    @commands.command(name="help")
    async def _help(self, ctx, *cmds, _all=False):
        if not cmds:
            embed = discord.Embed(color=discord.Color.blurple())
            embed.set_author(name=f"{ctx.me.display_name}'s Commands.", icon_url=ctx.me.avatar_url_as(format="png",
                                                                                                      size=32))
            embed.set_footer(text="Prefix: %s" % ctx.prefix)
            n = []
            for cog in self.bot.cogs.keys():
                if sum(1 for n in self.bot.get_cog_commands(cog) if not (n.hidden and not _all)) == 0:
                    continue
                n.append(f"**{cog}**\n")
                for cmd in self.formatter(self.bot.get_cog_commands(cog), ignore_hidden=_all):
                    n.append(cmd)
            embed.description = "".join(n)
            await ctx.send(embed=embed)
        else:
            if cmds[0] == "all":
                await ctx.invoke(self._help, _all=True)
            else:
                await ctx.invoke(self.bot._old_help, *cmds)


def setup(bot):
    bot._old_help = bot.remove_command("help")
    bot.add_cog(Help(bot))


def teardown(bot):
    bot.add_command(bot._old_help)
