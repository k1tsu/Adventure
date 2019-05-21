# -> Builtin modules
import io
import logging
import textwrap
import traceback
from contextlib import redirect_stdout

# -> Pip packages
import discord
from discord.ext import commands

# -> Local files
import blobs
import utils

log = logging.getLogger("Adventure.cogs.Moderator")


class Moderator(commands.Cog):
    """Commands for the owner.
    You shouldn't be seeing this."""
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    async def cog_check(self, ctx):
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
    async def addsupporter(self, ctx, *, user: discord.User):
        if not await self.bot.db.fetchrow("SELECT * FROM supporters WHERE userid=$1;", user.id):
            await self.bot.db.execute("INSERT INTO supporters VALUES ($1);", user.id)
            g = self.bot.get_guild(561390061963182132)
            m = g.get_member(user.id)
            if m:
                await self.bot.http.add_role(g.id, m.id, 561404670778802193)
            await ctx.send(f"{user} is now a supporter.")
        else:
            await ctx.send("User is already a supporter.")

    @commands.command(hidden=True)
    async def supporters(self, ctx):
        n = []
        for user in await self.bot.db.fetch("SELECT userid FROM supporters;"):
            uid = user['userid']
            u = self.bot.get_user(uid)
            n.append(f"{u or 'uncached'}")
        await ctx.send(", ".join(n))

    @commands.command(hidden=True)
    async def channelignore(self, ctx, *, num: int):
        if await self.bot.redis.sismember("channel_ignore", str(num)):
            await self.bot.redis.srem("channel_ignore", str(num))
            self.bot.player_manager.ignored_channels.remove(num)
            await ctx.add_reaction(blobs.BLOB_CROSS)
        else:
            await self.bot.redis.sadd("channel_ignore", str(num))
            self.bot.player_manager.ignored_channels.append(num)
            await ctx.add_reaction(blobs.BLOB_TICK)
        
    @commands.command(hidden=True)
    async def guildignore(self, ctx, *, num: int):
        if await self.bot.redis.sismember("guild_ignore", str(num)):
            await self.bot.redis.rem("guild_ignore", str(num))
            self.bot.player_manager.ignored_guilds.remove(num)
            await ctx.add_reaction(blobs.BLOB_CROSS)
        else:
            await self.bot.redis.sadd("guild_ignore", str(num))
            self.bot.player_manager.ignored_guilds.append(num)
            await ctx.add_reaction(blobs.BLOB_TICK)

    @commands.command(hidden=True)
    async def bl(self, ctx, member: discord.User, *, reason: str = "None provided.", silent=False):
        if len(reason) > 255:
            return await ctx.send("Limitation: Reason too long.", delete_after=10)
        if member.id not in self.bot.blacklist:
            self.bot.blacklist[member.id] = reason
            log.info("%s was blacklisted by %s." % (member, ctx.author))
        else:
            self.bot.blacklist.pop(member.id)
            log.info("%s was unblacklisted by %s." % (member, ctx.author))
        if not await ctx.safe_delete() and not silent:
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
    async def forcevote(self, ctx, user: int, weekend: bool = False):
        async with self.bot.session.post(
                "https://xuathegrate.xyz/vote",
                json={"user": str(user), "isWeekend": True},
                headers={"Authorization": self.bot.config.DBL_AUTH}
        ) as req:
            await ctx.send(f"{req.status}: {req.reason}")

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
            return await ctx.message.add_reaction(blobs.BLOB_TICK)

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
        await ctx.message.add_reaction(blobs.BLOB_TICK)

    @commands.command(hidden=True)
    async def dailyreset(self, ctx, *, member: discord.User):
        player = self.bot.player_manager.get_player(member)
        if not player:
            log.warning("%s / %s: No player for %s", ctx.message.clean_content, ctx.author, member)
            return await ctx.message.add_reaction(blobs.BLOB_CROSS)
        await self.bot.redis.set(f"daily_{member.id}", "12", "EX", "1")
        await ctx.message.add_reaction(blobs.BLOB_TICK)

    @commands.command(hidden=True)
    async def modspeedup(self, ctx, *, member: discord.User, ignore_reaction=False):
        player = self.bot.player_manager.get_player(member)
        if not player:
            log.warning("%s / %s: No player for %s", ctx.message.clean_content, ctx.author, member)
            return await ctx.message.add_reaction(blobs.BLOB_CROSS)
        if await player.is_travelling():
            await self.bot.redis.set(f"travelling_{member.id}", "0", "EX", "1")
        elif await player.is_exploring():
            await self.bot.redis.set(f"exploring_{member.id}", "0", "EX", "1")
        if not ignore_reaction:
            await ctx.message.add_reaction(blobs.BLOB_TICK)

    @commands.command(hidden=True)
    async def teleport(self, ctx, member: discord.User, *, map: str):
        player = self.bot.player_manager.get_player(member)
        if not player:
            log.warning("%s / %s: No player for %s", ctx.message.clean_content, ctx.author, member)
            return await ctx.message.add_reaction(blobs.BLOB_CROSS)
        try:
            map = self.bot.map_manager.resolve_map(map)
        except RuntimeError:
            log.warning("%s / %s: No map %s", ctx.message.clean_content, ctx.author, map)
            return await ctx.message.add_reaction(blobs.BLOB_CROSS)
        else:  # i dont remember if it returns none or not lol
            if map is None:
                log.warning("%s / %s: No map %s", ctx.message.clean_content, ctx.author, map)
                return await ctx.message.add_reaction(blobs.BLOB_CROSS)
            player.map = map
            await ctx.invoke(self.modspeedup, member=member)

    @commands.command(hidden=True)
    async def redis(self, ctx, *args):
        try:
            ret = await self.bot.redis.execute(*args)
            await ctx.send(getattr(ret, "decode", ret.__str__)())
        except Exception as e:
            await ctx.add_reaction(blobs.BLOB_CROSS)
            raise e
        else:
            await ctx.add_reaction(blobs.BLOB_TICK)

    @redis.error
    async def redis_error(self, ctx, exc):
        await ctx.send(f"`{exc}`")

    @commands.command(hidden=True, name='eval')
    async def _eval(self, ctx, *, body: str):
        """Evaluates a code"""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction(blobs.BLOB_TICK)
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.command(hidden=True)
    async def activejobs(self, ctx):
        table = utils.TabularData()
        table.set_columns(["owner", "ttl", "type"])
        for p in self.bot.player_manager.players:
            if await p.is_travelling():
                table.add_row([str(p.owner), await self.bot.redis.ttl(f"travelling_{p.owner.id}"), "travelling"])
            elif await p.is_exploring():
                table.add_row([str(p.owner), await self.bot.redis.ttl(f"exploring_{p.owner.id}"), "exploring"])
        await ctx.send(f"```\n{table.render()}\n```")

    @commands.command(hidden=True)
    async def logs(self, ctx):
        filename = f"logs/{self.bot.init.strftime('%Y-%m-%d_%H.%M.%S.%f')}.log"
        await ctx.invoke(self.bot.get_command("jishaku cat"), argument=filename)


def setup(bot):
    bot.add_cog(Moderator(bot))
