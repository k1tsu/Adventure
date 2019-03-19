import datetime
import logging

from discord.ext import commands

import utils


log = logging.getLogger("CommandLogger")
log.setLevel(logging.DEBUG)
log.handlers = [logging.FileHandler("logs/commands.log", "w", "utf-8")]

# [HH:MM:SS] ((guildid) guild / (channelid) #channel) (userid) user: command | error
FMT = "[{}] (({}) {} / ({}) #{}) ({}) {}: {}"
EMT = "[{}] (({}) {} / ({}) #{}) ({}) {}: {} | {}"

HEADERS = ["Time", "(Guild ID) Guild", "(Channel ID) #Channel", "(Author ID) Author", "Content", "Exception"]


class CommandLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("Logger initialized")

    @commands.Cog.listener("on_command_completion")
    @commands.Cog.listener("on_command_error")
    async def handlerrrrr(self, ctx, exc=None):
        exc = getattr(exc, "original", exc)
        if isinstance(exc, commands.CommandNotFound):
            return
        table = utils.TabularData()
        table.set_columns(HEADERS)
        if ctx.guild:
            table.add_row([datetime.datetime.utcnow().strftime("%H:%M:%S"), f"({ctx.guild.id}) {ctx.guild}",
                           f"({ctx.channel.id}) #{ctx.channel}", f"({ctx.author.id}) {ctx.author}",
                           ctx.message.clean_content, f"{type(exc).__name__}: {exc}" if exc else ""])
        else:
            table.add_row([datetime.datetime.utcnow().strftime("%H:%M:%S"), f"None",
                           f"None", f"({ctx.author.id}) {ctx.author}",
                           ctx.message.clean_content, f"{type(exc).__name__}: {exc}" if exc else ""])
        log.error(table.render())


def setup(bot):
    bot.add_cog(CommandLogger(bot))
