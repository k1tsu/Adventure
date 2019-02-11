from discord.ext import commands

import discord
import humanize

import utils

from datetime import datetime, timedelta

import logging
import traceback
log = logging.getLogger("Adventure.cogs.Handler")


EVENT_ERROR_FMT = """Error in %s
Args: %s
Kwargs: %s
%s
"""

CMD_ERROR_FMT = """Command error occured:
Guild: %s (%s)
User: %s (%s)
Invocation: %s
%s"""


class Handler:
    def __init__(self, bot):
        self.bot = bot

    async def on_command_error(self, ctx, exc, enf=False):
        if hasattr(ctx.command, "on_error") and not enf:
            return
        if hasattr(ctx.cog, f"_{ctx.cog.__class__.__name__}__error") and not enf:
            return
        exc = getattr(exc, "original", exc)
        if isinstance(exc, (commands.CommandNotFound, commands.NoPrivateMessage, commands.DisabledCommand)):
            return
        if isinstance(exc, commands.CommandOnCooldown):
            now = datetime.now()
            later = timedelta(seconds=exc.retry_after)
            fmt = humanize.naturaltime(now + later)
            return await ctx.send(":warning: Ratelimited. Try again in %s." % fmt)
        ctx.command.reset_cooldown(ctx)
        if isinstance(exc, utils.AdventureBase):
            return await ctx.send(str(exc))
        if isinstance(exc, commands.BadArgument):
            return await ctx.invoke(self.bot.get_command("help"), *ctx.command.qualified_name.split())
        if isinstance(exc, commands.TooManyArguments):
            return await ctx.send(f"{ctx.command} doesn't take any extra arguments."
                                  f" See `{ctx.prefix}help {ctx.command}")
        if isinstance(exc, commands.MissingRequiredArgument):
            return await ctx.send(f"You must fill in the \"{exc.param.name}\" parameter.")
        if isinstance(exc, (commands.NotOwner, commands.MissingPermissions)):
            return await ctx.send("You don't have permission to use this command.")
        if isinstance(exc, commands.BotMissingPermissions):
            return await ctx.send("I don't have permission to execute this command.")
        log.error(CMD_ERROR_FMT, ctx.guild.name, ctx.guild.id,
                  str(ctx.author), ctx.author.id,
                  ctx.message.content, utils.format_exception(exc))
        await ctx.send(":exclamation: Something went wrong.")

    async def on_error(self, event, *args, **kwargs):
        if not self.bot.prepared.is_set():
            await self.bot.change_presence(status=discord.Status.dnd)
        log.error(EVENT_ERROR_FMT, event, args, kwargs, traceback.format_exc())


def setup(bot):
    bot.add_cog(Handler(bot))
