import asyncio
import json
import logging
import operator
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
    '2\u20e3': fight,
    '3\u20e3': surrender
}


async def send_action(demon, bot):
    ret = None
    content = """1\u20e3: Fight
2\u20e3: Use an item (doesnt work, redirects to fight)
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


_MESSAGES = {
    "resist": "{tdemon.owner}'s __{tdemon}__ **resists** `{move}` and took {damage} damage!",
    "absorb": "{tdemon.owner}'s __{tdemon}__ **absorbs** `{move}`! Healed for {damage} HP!",
    "reflect": "{tdemon.owner}'s __{tdemon}__ **reflects** `{move}`! {ademon.owner}'s _"
               "_{ademon}__ took {damage} damage!",
    "immune": "{tdemon.owner}'s __{tdemon}__ is **immune** to `{move}`!",
    "normal": "{tdemon.owner}'s __{tdemon}__ took {damage} damage!",
    "weak": "{tdemon.owner}'s __{tdemon}__ is **weak** to `{move}` and took {damage} damage!",
    "evade": "{tdemon.owner}'s __{tdemon}__ evaded the attack!"
}


async def battle_loop(ctx, alpha, beta):
    while not alpha.is_fainted() and not beta.is_fainted():
        loop = ctx.bot.loop
        t_alpha = loop.create_task(send_action(alpha, ctx.bot))
        t_beta = loop.create_task(send_action(beta, ctx.bot))
        await asyncio.wait([t_alpha, t_beta],
                           return_when=asyncio.ALL_COMPLETED)
        surr = t_alpha.exception() or t_beta.exception()
        if isinstance(surr, UserSurrended):
            if surr.user == alpha.owner.owner:
                await ctx.send(f"{alpha.owner} surrendered! {beta.owner} won!")
            else:
                await ctx.send(f"{beta.owner} surrendered! {alpha.owner} won!")
            # TODO: free gold
            return

        m_alpha = t_alpha.result()
        m_beta = t_beta.result()
        # await ctx.send((m_alpha, m_beta))

        dt_alpha, res_alpha = alpha.take_damage(beta, m_beta.type, m_beta.severity)
        msg_a = _MESSAGES[res_alpha.name].format(tdemon=alpha, move=m_beta.name, ademon=beta, damage=dt_alpha)

        dt_beta, res_beta = beta.take_damage(alpha, m_alpha.type, m_alpha.severity)
        msg_b = _MESSAGES[res_beta.name].format(tdemon=beta, move=m_alpha.name, ademon=alpha, damage=dt_beta)

        await ctx.send(msg_a + "\n" + msg_b)
    if alpha.is_fainted():
        msg = f"{alpha} fainted! {beta.owner} and their {beta} won!\nYou were given 5,000 G as a reward!"
        beta.owner.gold += 5000
    elif beta.is_fainted():
        msg = f"{beta} fainted! {alpha.owner} and their {alpha} won!\nYou were given 5,000 G as a reward!"
        alpha.owner.gold += 5000
    else:
        ctx.bot.wtf = ctx, alpha, beta
        raise RuntimeError("no one fainted? might have surrendered")
    await ctx.send(msg)


async def try_get_demon(ctx, player):
    em = ctx.bot.enemy_manager
    demons = {e.name for e in sorted(em.enemies, key=lambda e: e.id) if player.compendium.is_enemy_recorded(e)}
    demons &= ctx.cog.valid
    await player.owner.send(f"{blobs.BLOB_THINK} Choose a demon!")
    await ctx.paginate(*demons, destination=player.owner)
    demons = set(map(str.lower, demons))

    def checker(m):
        return m.content.lower() in demons and \
            not m.guild and \
            m.author == player.owner

    rs = [str(blobs.BLOB_TICK), str(blobs.BLOB_CROSS)]

    def rchecker(r, u):
        return str(r) in rs and \
            u == player.owner and \
            r.message.id == n.id

    while True:
        choice = await ctx.bot.wait_for("message", check=checker)
        name = choice.content.title()
        n = await player.owner.send(f"{blobs.BLOB_THINK} Are you sure you want to battle with {name}?")
        for r in rs:
            await n.add_reaction(r)
        r, _ = await ctx.bot.wait_for("reaction_add", check=rchecker, timeout=10)
        if str(r) == rs[0]:
            break

    data = await ctx.bot.db.fetchrow("SELECT * FROM persona_lookup WHERE name=$1;", name)

    return utils.BattleDemon(name=data['name'], owner=player, hp=data['hp'], moves=data['moves'], stats=data['stats'],
                             resistances=data['resistances'])


class Battle(commands.Cog):
    """Contains the commands for battle related commands.
    These (will) include Boss Fights and PvP battles."""
    def __init__(self, bot):
        self.bot = bot
        self._fighting = _Dict()
        self._battles = _TupleDict()
        self.valid = None
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
                        exc = task.exception()
                        if exc:
                            userid = self.bot.config.OWNERS[0]
                            user = self.bot.get_user(userid)
                            await user.send(utils.format_exception(exc))
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

    @commands.command()
    async def fight(self, ctx, *, user: discord.Member):
        """Fight another user in a battle to the death!
        Choose a demon from your compendium and battle it out.
        Each demon has their own unique moveset, stats and hitpoints.

        WARNING: If you time out any menu, it will count as a forfeit.

        (disclaimer: not actually to the death)"""
        if not self.valid:
            self.valid = set(map(operator.itemgetter('name'),
                                 await self.bot.db.fetch("SELECT name FROM persona_lookup")))
        alpha = self._pm.get_player(ctx.author)
        if not alpha:
            raise utils.NoPlayer

        if alpha.compendium.count == 0:
            return await ctx.send(f"{blobs.BLOB_THINK} You haven't found any demons yet.")

        beta = self._pm.get_player(user)
        if not beta:
            return await ctx.send(f"{blobs.BLOB_PLSNO} {user} doesn't have a player!")

        if beta.compendium.count == 0:
            return await ctx.send(f"{blobs.BLOB_THINK} {user} hasn't found any demons yet.")

        if not await ctx.warn(f"{blobs.BLOB_THINK} {user}, do you want to battle {ctx.author}?", waiter=user):
            return await ctx.send(f"{blobs.BLOB_SAD} {user} did not want to fight.")

        t1 = self.bot.loop.create_task(try_get_demon(ctx, alpha))
        t2 = self.bot.loop.create_task(try_get_demon(ctx, beta))

        _, dnf = await asyncio.wait([t1, t2], return_when=asyncio.ALL_COMPLETED, timeout=120)
        if len(dnf) > 0:
            t1.cancel(), t1.result(), t1.exception()
            t2.cancel(), t2.result(), t2.exception()
            # idk if this is even useful but ok
            return await ctx.send(f"{blobs.BLOB_SAD} Everyone didn't finish in time.")

        self._fighting[ctx.author.id] = user.id

        p1 = t1.result()
        p2 = t2.result()

        key = (ctx.author.id, user.id)

        if p1.agility >= p2.agility:
            self._battles[key] = self.bot.loop.create_task(battle_loop(ctx, p1, p2))
        else:
            self._battles[key] = self.bot.loop.create_task(battle_loop(ctx, p2, p1))

        await ctx.send("Begin!")
        if not self.task_ender.done():
            self.task_ender.cancel()
        self.task_ender = self.bot.loop.create_task(self._task_ender())

    @fight.before_invoke
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
