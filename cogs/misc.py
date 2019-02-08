from discord.ext import commands
import discord

import io
import time

from utils import TabularData, format_exception


class Misc:
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def cleanup_code(content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @commands.command()
    async def ping(self, ctx):
        start = time.perf_counter()
        await ctx.author.trigger_typing()
        end = time.perf_counter() - start
        await ctx.send(f":ping_pong: **{end*1000:.2f}ms**")

    @commands.command()
    async def source(self, ctx):
        await ctx.send("<https://github.com/XuaTheGrate/Adventure>")

    @commands.command(hidden=True)
    @commands.is_owner()
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
            return await ctx.send(f'```py\n{format_exception(e)}\n```')

        rows = len(results)
        if is_multistatement or rows == 0:
            return await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

        headers = list(results[0].keys())
        table = TabularData()
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
    bot.add_cog(Misc(bot))
