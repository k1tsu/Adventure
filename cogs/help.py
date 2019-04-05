import discord
from discord.ext import commands

import utils


class CommandOrCog(commands.Converter):
    async def convert(self, ctx, argument):
        arg = ctx.bot.get_cog(argument) or ctx.bot.get_command(argument)
        if not arg:
            raise commands.BadArgument(f"Couldn't find a command / module named {argument}.")
        return arg


class Help2(commands.Cog):
    """
    Provides information on how to use a command.
    """
    def __init__(self, bot):
        self.bot = bot

    def formatter(self, i, *, stack=0, show=False):
        for command in i:
            if command.hidden and not show:
                continue
            if command.help:
                line = f"- " + command.help.split("\n")[0]
            else:
                line = ""
            yield "\u200b " * (stack*2) + f"►**{command}** " + line
            if isinstance(command, commands.Group):
                yield from self.formatter(command.commands, stack=stack+1, show=show)

    def parents(self, i):
        if i.parent:
            yield from self.parents(i.parent)
        yield i.name

    @commands.command()
    async def help(self, ctx, *, item: CommandOrCog = None):
        show = await self.bot.is_owner(ctx.author)
        embed = discord.Embed(colour=discord.Colour(11059565), description="")
        embed.set_author(name="Adventure!'s Commands", icon_url=ctx.me.avatar_url_as(format="png", size=32))
        embed.set_footer(text=f"Use {ctx.prefix}help <command/module> for more help!")
        if not item:
            # no item, we show all cogs
            for cog in self.bot.cogs.values():
                if sum(1 for c in cog.get_commands() if not (not show and c.hidden)) == 0:
                    continue
                doc = cog.__doc__.split('\n')[0] if cog.__doc__ else 'No help provided'
                embed.description += f"►**{cog.qualified_name}**\n\u200b\t\u200b\t{doc}\n"
        else:
            if isinstance(item, commands.Cog):
                embed.title = item.qualified_name
                embed.description += f"{item.__doc__}\n\n"
                embed.description += "\n".join(self.formatter(item.get_commands(), show=show))
            else:
                embed.title = " ".join(self.parents(item))
                if item.help:
                    embed.description += item.help + '\n\n'
                else:
                    embed.description = += "No help provided.\n\n"
                if isinstance(item, commands.Group):
                    embed.description += '\n'.join(self.formatter(item.commands, show=show))
        await ctx.send(embed=embed)


def setup(bot):
    bot.old_help = bot.remove_command("help")
    bot.add_cog(Help2(bot))

def teardown(bot):
    bot.add_command(bot.old_help)
