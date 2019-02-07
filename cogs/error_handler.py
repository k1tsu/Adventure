import logging
import traceback
from discord.ext import commands
import humanize
from datetime import datetime, timedelta

log = logging.getLogger("Adventure.cogs.Handler")


def format_traceback(exc: BaseException):
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


ERROR_FMT = """Command error occured:
Guild: %s (%s)
User: %s (%s)
Invocation: %s
%s"""


class Handler:
    def __init__(self, bot):
        self.bot = bot

    async def on_command_error(self, ctx, exc):
        exc = getattr(exc, "original", exc)
        if isinstance(exc, commands.CommandOnCooldown):
            now = datetime.now()
            later = timedelta(seconds=exc.retry_after)
            fmt = humanize.naturaltime(now + later)
            return await ctx.send(":warning: Ratelimited. Try again in %s." % fmt)
        ctx.command.reset_cooldown(ctx)
        if isinstance(exc, commands.UserInputError):
            return await ctx.invoke(self.bot.get_command("help"), *ctx.command.qualified_name.split())
        if isinstance(exc, (commands.CommandNotFound, commands.NoPrivateMessage, commands.DisabledCommand)):
            return
        if isinstance(exc, (commands.NotOwner, commands.MissingPermissions)):
            return await ctx.send("You don't have permission to use this command.")
        if isinstance(exc, commands.BotMissingPermissions):
            return await ctx.send("I don't have permission to execute this command.")
        log.error(ERROR_FMT, ctx.guild.name, ctx.guild.id,
                  str(ctx.author), ctx.author.id,
                  ctx.message.content, format_traceback(exc))
        await ctx.send(":exclamation: Something went wrong.")


def setup(bot):
    bot.add_cog(Handler(bot))
