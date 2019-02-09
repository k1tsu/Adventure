from discord.ext import commands
import discord

import io
from typing import Union
import logging
log = logging.getLogger("Adventure.cogs.Moderator")

import utils


class Moderator:
    def __init__(self, bot):
        self.bot = bot

    async def __local_check(self, ctx):
        if ctx.author.id not in self.bot.config.OWNERS:
            raise commands.NotOwner
        return True

    @staticmethod
    def cleanup_code(content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @commands.command(hidden=True)
    async def bl(self, ctx, member: Union[discord.Member, discord.User], reason: str = "None provided."):
        if len(reason) > 255:
            return await ctx.send("Limitation: Reason too long.", delete_after=10)
        if member.id not in self.bot.blacklist:
            self.bot.blacklist[member.id] = reason
            log.info("%s was blacklisted by %s." % (member, ctx.author))
        else:
            self.bot.blacklist.pop(member.id)
            log.info("%s was unblacklisted by %s." % (member, ctx.author))
        if not await ctx.safe_delete():
            await ctx.add_reaction("\N{OK HAND SIGN}")

    @commands.command(hidden=True)
    async def vbl(self, ctx):
        n = ["```prolog"]
        size = max([len(str(self.bot.get_user(u) or 'Not cached')) for u in self.bot.blacklist])
        fmt = [f"{str(u): >18} ~ {str(self.bot.get_user(u) or 'Not cached'): >{size}} : {r}"
               for u, r in self.bot.blacklist.items()]
        n.extend(fmt)
        n.append("```")
        await ctx.send("\n".join(n) or "Nothing found.")

    @commands.command(hidden=True)
    async def sql(self, ctx, *, query):

        query = self.cleanup_code(query)

        is_multistatement = query.count(';') > 1
        if is_multistatement:
            # fetch does not support multiple statements
            strategy = self.bot.db.execute
        else:
            strategy = self.bot.db.fetch

        try:
            results = await strategy(query)
        except Exception as e:
            return await ctx.send(f'```py\n{utils.format_exception(e)}\n```')

        rows = len(results)
        if is_multistatement or rows == 0:
            return await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

        headers = list(results[0].keys())
        table = utils.TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f'```\n{render}\n```'
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode('utf-8'))
            await ctx.send('Too many results...', file=discord.File(fp, 'results.txt'))
        else:
            await ctx.send(fmt)
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")


def setup(bot):
    bot.add_cog(Moderator(bot))
