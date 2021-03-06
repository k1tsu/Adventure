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
        clean = ctx.message.clean_content.replace("\n", "\\n")
        log.error(f"[{ctx.message.created_at}] {ctx.guild} / {ctx.author}: {clean} |"
                  f" {(type(exc).__name__ + ': ' + str(exc)) if exc else ''}")


def setup(bot):
    bot.add_cog(CommandLogger(bot))
