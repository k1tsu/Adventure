import asyncio
import json
import logging
from collections import namedtuple

import discord
from discord.ext import commands

import blobs
import utils


log = logging.getLogger("Adventure.Battle")
log.setLevel(logging.DEBUG)


class _Dict(dict):
    def _check_item(self, item):
        if item in self.keys():
            return item
        elif item in self.values():
            return dict({v: k for k, v in self.items()})[item]
        raise KeyError(repr(item))

    def __getitem__(self, item):
        if item in self.keys():
            return dict.__getitem__(self, item)
        elif item in self.values():
            return dict({v: k for k, v in self.items()})[item]
        else:
            raise KeyError(repr(item))

    def pop(self, i):
        topop = self._check_item(i)
        return dict.pop(self, topop)

    def __contains__(self, item):
        return item in self.keys() or item in self.values()


class _TupleDict(dict):
    def _check_item(self, item):
        if isinstance(item, tuple):
            if item in self.keys():
                return item
        for t in self.keys():
            if item in t:
                return t
        raise KeyError(repr(item))

    def __getitem__(self, item):
        if isinstance(item, tuple):
            return dict.__getitem__(self, item)
        for t in self.keys():
            if item in t:
                return dict.__getitem__(self, t)
        raise KeyError(repr(item))

    def __setitem__(self, key, value):
        if not isinstance(key, tuple):
            raise ValueError("expected <class 'tuple'>, got {.__class__!r}".format(key))
        dict.__setitem__(self, key, value)

    def pop(self, i):
        topop = self._check_item(i)
        return dict.pop(self, topop)

    def __contains__(self, item):
        return any(item in key for key in self.keys())


class UserSurrended(Exception):
    def __init__(self, user):
        super().__init__()
        self.user = user


move = namedtuple("move", "name type severity")


async def surrender(demon, bot):
    user = demon.owner.owner
    msg = await user.send("Are you sure you want to surrender the battle?")

    rs = [str(blobs.BLOB_TICK), str(blobs.BLOB_CROSS)]

    for r in rs:
        await msg.add_reaction(r)

    def r_check(r, u):
        return u == user and \
            str(r) in rs and \
            type(u) is discord.User

    try:
        r, _ = await bot.wait_for("reaction_add", check=r_check, timeout=30)
    except asyncio.TimeoutError:
        raise UserSurrended(user)
    else:
        if str(r) == rs[0]:
            raise UserSurrended(user)
    finally:
        await msg.delete()


async def fight(demon, bot):
    print(f"{demon}, {demon.name}, {demon.owner}")
    user = demon.owner.owner
    _moves = await bot.db.fetchval("SELECT moves FROM persona_lookup WHERE name=$1;", demon.name)
    print(f"_moves")
    moves = json.loads(_moves)
    if not moves:
        raise RuntimeError(f"No moves found for demon {demon.name}")

    rctn = list(enumerate(moves.keys()))

    content = ("Select a move!\n\n" +
               "\n".join(f"{i}\u20e3: {m}" for i, m in rctn))
    msg = await user.send(content + '\n\u21a9 Go back')

    reacts = {f"{i}\u20e3": v for i, v in rctn}
    reacts['\u21a9'] = "__go_back"

    for r in reacts:
        await msg.add_reaction(r)

    def react_check(r, u):
        return str(r) in reacts and \
            u == user and \
            not r.message.guild

    while True:
        try:
            reaction, _ = await bot.wait_for("reaction_add", check=react_check, timeout=120)
        except asyncio.TimeoutError:
            await surrender(user, bot)
        else:
            if str(reaction) == '\u21a9':
                return None
            name = reacts[str(reaction)]
            type_, severity = moves[name]
            return move(name, type_, severity)
        finally:
            await msg.delete()


_CHOICES = {
    '1\u20e3': fight,
    '3\u20e3': surrender
}


async def send_action(demon, bot):
    ret = None
    content = """1\u20e3: Fight
2\u20e3: Use an item (doesnt work)
3\u20e3: Surrender"""
    user = demon.owner.owner
    while ret is None:
        msg = await user.send(content)

        for a in range(1, 4):
            await msg.add_reaction(f'{a}\u20e3')

        def wait_check(r, u):
            return len(str(r)) > 1 and \
                str(r)[1] == '\u20e3' and \
                not r.message.guild and \
                u == user

        try:
            choice, _ = await bot.wait_for("reaction_add", check=wait_check, timeout=120)
        except asyncio.TimeoutError:
            choice = "3\u20e3"
        finally:
            await msg.delete()
            # noinspection PyUnboundLocalVariable
            choice = str(choice)

        func = _CHOICES[choice]

        ret = await func(demon, bot)

    return ret


async def battle_loop(ctx, alpha, beta):
    while not alpha.is_fainted() and not beta.is_fainted():
        ((t_alpha, t_beta), _) = await asyncio.wait([send_action(alpha, ctx.bot), send_action(beta, ctx.bot)],
                                                    return_when=asyncio.ALL_COMPLETED)
        surr = t_alpha.exception() or t_beta.exception()
        if isinstance(surr, UserSurrended):
            dee = alpha.owner if surr.user == beta.owner else beta.owner
            der = alpha.owner if surr.user != beta.owner else beta.owner
            return await ctx.send(f"{der} surrendered! {dee} won!")
            # TODO: free gold

        await ctx.send(f"ALPHA {alpha.owner}: {t_alpha.result()}")
        await ctx.send(f"BETA {beta.owner}: {t_beta.result()}")
        break


class Battle(commands.Cog):
    """Contains the commands for battle related commands.
    These (will) include Boss Fights and PvP battles."""
    def __init__(self, bot):
        self.bot = bot
        self._fighting = _Dict()
        self._battles = _TupleDict()
        self.task_ender = self.bot.loop.create_task(self._task_ender())

    async def _task_ender(self):
        while await asyncio.sleep(0, True):
            try:
                if not self._battles:
                    break
                for users, task in list(self._battles.items()).copy():
                    # print((users, task))
                    if task.done():
                        self._battles.pop(users[0])
                        self._fighting.pop(users[0])
            except asyncio.CancelledError:
                break

    @property
    def _pm(self):
        return self.bot.player_manager

    @staticmethod
    async def can_send_dm(user):
        try:
            await user.send("")
        except discord.Forbidden:
            return False
        except discord.HTTPException as exc:
            if exc.status == 400:
                return True
            raise
        except Exception:
            raise

    @commands.command(hidden=True)
    async def _fight(self, ctx, *, user: discord.Member):
        """Fight another user in a battle to the death!
        Choose a demon from your compendium and battle it out.
        Each demon has their own unique moveset, stats and hitpoints.

        WARNING: If you time out any menu, it will count as a forfeit.

        (disclaimer: not actually to the death)"""
        alpha = self._pm.get_player(ctx.author)
        if not alpha:
            raise utils.NoPlayer

        beta = self._pm.get_player(user)
        if not beta:
            return await ctx.send(f"{blobs.BLOB_PLSNO} {user} doesn't have a player!")

        if not await ctx.warn(f"{blobs.BLOB_THINK} {user}, do you want to battle {ctx.author}?", waiter=user):
            return await ctx.send(f"{blobs.BLOB_SAD} {user} did not want to fight.")

        self._fighting[ctx.author.id] = user.id

        await ctx.send(f"{blobs.BLOB_THINK} This command is in beta.\n"
                       "Both of you will be given Arsene for the time being.")

        _p_raw = await self.bot.db.fetchrow("SELECT * FROM persona_lookup WHERE name='Arsene';")

        p1, p2 = (utils.BattleDemon(owner=alpha, hp=_p_raw['hp'], moves=_p_raw['moves'],
                                    stats=_p_raw['stats'], name=_p_raw['name']),
                  utils.BattleDemon(owner=beta, hp=_p_raw['hp'], moves=_p_raw['moves'],
                                    stats=_p_raw['stats'], name=_p_raw['name']))

        key = (ctx.author.id, user.id)
        self._battles[key] = self.bot.loop.create_task(battle_loop(ctx, p1, p2))
        await ctx.send("Begin!")
        if not self.task_ender.done():
            self.task_ender.cancel()
        self.task_ender = self.bot.loop.create_task(self._task_ender())

    @_fight.before_invoke
    async def pre_invoke_hook(self, ctx):
        user = ctx.kwargs.get("user")

        if ctx.author.id in self._fighting:
            u = self.bot.get_user(self._fighting[ctx.author.id])
            await ctx.send(f"{blobs.BLOB_ARMSCROSSED} You are already fighting {u}!")
            raise utils.IgnoreThis

        if user.id in self._fighting:
            u = self.bot.get_user(self._fighting[user.id])
            await ctx.send(f"{blobs.BLOB_ARMSCROSSED} {user} is already fighting {u}!")

        if not await self.can_send_dm(ctx.author):
            await ctx.send(f"{blobs.BLOB_ANGERY} You must enable your DMs for this feature.")
            raise utils.IgnoreThis

        if not await self.can_send_dm(user):
            await ctx.send(f"{blobs.BLOB_ANGERY} {user} does not have their DMs open.")
            raise utils.IgnoreThis


def setup(bot):
    bot.add_cog(Battle(bot))
