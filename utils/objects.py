# -> Builtin modules
import collections
import enum
import random
import logging
import math
import operator
from typing import *
from datetime import datetime, timedelta

# -> Pip packages
import humanize

# -> Local files
import blobs
import utils

maplog = logging.getLogger("Adventure.MapManager")
plylog = logging.getLogger("Adventure.PlayerManager")


class Status(enum.Enum):
    idle = 0
    travelling = 1
    exploring = 2


class Dummy:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class Map:
    def __init__(self, **kwg):
        self._raw = kwg.copy()
        self.id = kwg.get("id")
        self.name = kwg.get("name")
        self.nearby = list()
        self.density = kwg.get("density")
        self.description = kwg.get("description")
        self._nearby = []
        self.is_safe = kwg.get("safe", False)

    def __repr__(self):
        return f"<Map id={self.id} name='{self.name}'>"

    def __eq__(self, other):
        return isinstance(other, type(self)) and other.id == self.id

    def __str__(self):
        return self.name

    def __int__(self):
        return self.id

    def calculate_travel_to(self, other) -> float:
        if isinstance(other, self.__class__):
            return (self.density + other.density) / 2468
        elif isinstance(other, Player):
            return (self.density + other.map.density) / (2468 * (1 if not other.has_explored(self) else 4))
        else:
            raise RuntimeError

    def calculate_explore(self) -> float:
        return ((self.density * 2468) / (1000 ** 2)) / 2

    def travel_exp(self, map) -> int:
        if not isinstance(map, (self.__class__, Player)):
            raise RuntimeError
        time = self.calculate_travel_to(map) * 10
        return math.floor(time / 3)

    def explore_exp(self) -> int:
        return math.floor(self.calculate_explore() * 15)


class Player:

    def __init__(self, **kwg):
        self._bot = kwg.get("bot")
        self.owner = kwg.get("owner")
        self.name = kwg.get("name")
        self._map = self._bot.map_manager.get_map(0)
        self._next_map = kwg.get("next_map", None)
        if self._next_map is not None:
            self._next_map = self._bot.map_manager.resolve_map(self._next_map)
        self.exp = kwg.get("exp", 1)
        self._next_level = self.level + 1
        self.created_at = kwg.get("created_at")
        self._explored_maps = kwg.get("explored", [self._bot.map_manager.get_map(0)])
        self.status = kwg.get("status", Status.idle)
        self.gold = kwg.get("gold", 0)
        rd = kwg.get("compendium", None)
        if not rd:
            self.raw_compendium_data = [0] * 237
        else:
            self.raw_compendium_data = rd
        self.compendium = Compendium(self)

    def __repr__(self):
        return "<Player name='{0.name}' owner={0.owner!r} exp={0.exp} coins={0.gold}>".format(self)

    def __str__(self):
        return self.name

    @property
    def healthpoints(self) -> float:
        return self.strength * 2

    @property
    def strength(self) -> float:
        return self.exp / self.level

    @property
    def next_map(self) -> Map:
        return self._next_map

    @next_map.setter
    def next_map(self, value):
        self._next_map = self._bot.map_manager.resolve_map(value)

    @property
    def level(self) -> int:
        return min(99, math.floor(self.exp ** .334))

    @property
    def explored_maps(self) -> List[Map]:
        return self._explored_maps

    @explored_maps.setter
    def explored_maps(self, value):
        self._explored_maps = list(map(self._bot.map_manager.get_map, value))

    @property
    def is_admin(self) -> bool:
        return self.owner.id in self._bot.config.OWNERS

    @property
    def map(self) -> Map:
        return self._map

    @map.setter
    def map(self, value):
        self._map = self._bot.map_manager.resolve_map(value)

    # -- Checks -- #

    async def is_travelling(self) -> bool:
        return await self.travel_time() > 0

    async def is_exploring(self) -> bool:
        return await self.explore_time() > 0

    # -- Updaters -- #

    async def update(self, ctx):
        if await self.update_travelling():
            await ctx.channel.send("{} {} has arrived at {}!".format(blobs.BLOB_PARTY, self, self.map))
        elif await self.update_exploring():
            await ctx.channel.send("{} {} has finished exploring {}!".format(blobs.BLOB_PARTY, self, self.map))
        if self.update_level():
            await ctx.channel.send("{} {} levelled to tier **{}**!".format(blobs.BLOB_PARTY, self, self.level))

    def update_level(self) -> bool:
        if self.level >= self._next_level:
            self._next_level = self.level + 1
            return True
        return False

    async def update_travelling(self) -> bool:
        if await self.is_travelling():
            if self.next_map is None:
                dest = await self._bot.redis("GET", f"next_map_{self.owner.id}")
                self.next_map = dest.decode()
            return False  # the TTL hasnt expired
        if self.next_map is None:
            dest = await self._bot.redis("GET", f"next_map_{self.owner.id}")
        else:
            dest = self.next_map.id
        if dest is None:
            return False  # the player isnt travelling at all
        self.exp += self.map.travel_exp(self.next_map)
        self._next_map = None
        plylog.info("%s has arrived at their location.", self.name)
        self.map = dest
        await self._bot.redis("DEL", f"next_map_{self.owner.id}")
        await self._bot.redis("SET", f"status_{self.owner.id}", "0")
        self.status = Status.idle
        return True

    async def update_exploring(self) -> bool:
        if await self.is_exploring():
            return False
        if self.status == Status.exploring or await self._bot.redis("GET", f"status_{self.owner.id}") == 2:
            plylog.info("%s has finished exploring %s.", self.name, self.map)
            await self._bot.redis("SET", f"status_{self.owner.id}", "0")
            self.status = Status.idle
            self.exp += self.map.explore_exp()
            return True

    async def travel_time(self) -> int:
        if not self.next_map:
            self.next_map = await self._bot.redis("GET", f"next_map_{self.owner.id}")
        return await self._bot.redis("TTL", f"travelling_{self.owner.id}")

    async def explore_time(self) -> int:
        return await self._bot.redis("TTL", f"exploring_{self.owner.id}")

    # -- Real functions -- #

    def has_explored(self, map: Map):
        return map.is_safe or map in self.explored_maps

    def exp_to_next_level(self):
        next_exp = self._next_level ** 3
        return next_exp - self.exp

    async def travel_to(self, destination):
        if await self.is_travelling():
            raise utils.AlreadyTravelling(self.name,
                                          humanize.naturaltime((datetime.now() + timedelta(
                                              seconds=await self.travel_time()))))
        elif await self.is_exploring():
            raise utils.AlreadyTravelling(self.name,
                                          humanize.naturaltime((datetime.now() + timedelta(
                                              seconds=await self.explore_time()))))
        time = int(((datetime.now() + timedelta(hours=destination.calculate_travel_to(self))) - datetime.now()
                    ).total_seconds())
        self.next_map = destination
        plylog.info("%s is adventuring to %s and will finish in %.2f hours.",
                    self.name, destination, destination.calculate_travel_to(self))
        await self._bot.redis("SET", f"travelling_{self.owner.id}", str(time), "EX", str(time))
        await self._bot.redis("SET", f"next_map_{self.owner.id}", str(destination.id))
        await self._bot.redis("SET", f"status_{self.owner.id}", "1")
        self.status = Status.travelling

    async def explore(self):
        if await self.is_travelling():
            raise utils.AlreadyTravelling(self.name,
                                          humanize.naturaltime((datetime.now() + timedelta(
                                              seconds=await self.travel_time()))))
        if await self.is_exploring():
            raise utils.AlreadyTravelling(self.name,
                                          humanize.naturaltime((datetime.now() + timedelta(
                                              seconds=await self.explore_time()))))
        if self.map in self._explored_maps:
            raise utils.AlreadyExplored(self.map)
        time = int(((datetime.utcnow() + timedelta(hours=self.map.calculate_explore())
                     ) - datetime.utcnow()).total_seconds())
        plylog.info("%s is exploring %s and will finish in %.2f hours.",
                    self.name, self.map, self.map.calculate_explore())
        await self._bot.redis("SET", f"exploring_{self.owner.id}", str(time), "EX", str(time))
        await self._bot.redis("SET", f"status_{self.owner.id}", "2")
        self.status = Status.exploring
        self._explored_maps.append(self.map)

    async def save(self, *, cursor=None):
        q = """
INSERT INTO players (owner_id, name, map_id, created_at, explored, exp, compendium_data, gold)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
ON CONFLICT (owner_id)
DO UPDATE
SET name = $2, map_id = $3, explored = $5, exp = $6, compendium_data = $7, gold = $8
WHERE players.owner_id = $1;
        """
        if not cursor:
            await self._bot.db.execute(q, self.owner.id, self.name, self._map.id, self.created_at,
                                       list(map(operator.attrgetter("id"), self.explored_maps)), self.exp,
                                       self.raw_compendium_data, self.gold)
        else:
            await cursor.execute(q, self.owner.id, self.name, self._map.id, self.created_at,
                                 list(map(operator.attrgetter("id"), self.explored_maps)), self.exp,
                                 self.raw_compendium_data, self.gold)

    async def delete(self, *, cursor=None):
        if not cursor:
            await self._bot.db.execute("DELETE FROM players WHERE owner_id=$1;", self.owner.id)
        else:
            await cursor.execute("DELETE FROM players WHERE owner_id=$1;", self.owner.id)
        await self._bot.redis("DEL", f"travelling_{self.owner.id}")
        await self._bot.redis("DEL", f"next_map_{self.owner.id}")
        await self._bot.redis("DEL", f"exploring_{self.owner.id}")
        await self._bot.redis("DEL", f"status_{self.owner.id}")
        self._bot.player_manager.players.remove(self)
        plylog.info("Player \"%s\" was deleted. (%s [%s])", self.name, self.owner, self.owner.id)
        del self


class Item:
    def __init__(self, *, id, name, cost):
        self.id = id
        self.name = name
        self.cost = cost

    def __repr__(self):
        return f'<Item id={self.id} name="{self.name}" cost={self.cost}>'


class Enemy:
    def __init__(self, *, id, name, maps, tier):
        self.id: int = id
        self.name: str = name
        self.maps: List[Map] = maps
        self.tier: int = tier

    def __repr__(self):
        return '<Enemy id={0.id} name="{0.name}" maps={0.maps} tier={0.tier}>'.format(self)

    def defeat(self, tier):
        diff = (tier ** 2) / (self.tier ** 2)
        normalized = math.tanh(diff / 4.6)
        ret = random.randint(1, 100) < round(normalized * 100)
        return ret


class Compendium:
    def __init__(self, player):
        self.player = player
        # noinspection PyProtectedMember
        self._bot = player._bot

    def __repr__(self):
        return "<Compendium owner={0.player.owner!r} flags={0.count}>".format(self)

    @property
    def count(self):
        return sum(self.bits)

    @property
    def bits(self):
        return self.player.raw_compendium_data

    def record_enemy(self, enemy):
        if self.is_enemy_recorded(enemy):
            raise ValueError("Enemy is already in book.")
        self.player.raw_compendium_data[enemy.id-1] = 1

    def is_enemy_recorded(self, enemy):
        return self.bits[enemy.id-1]

    def format(self):
        fin = [e.name for e in sorted(self._bot.enemy_manager.enemies, key=lambda e: e.id) if self.is_enemy_recorded(e)]
        table = utils.TabularData()
        headers = fin[:2]
        rest = fin[2:]
        table.set_columns(headers)
        if rest:
            chunks = [rest[x:x+2] if len(rest[x:x+2]) == 2 else [rest[x], ''] for x in range(0, len(rest), 2)]
            table.add_rows(chunks)
        return table.render()


class TypeDict(dict):
    _k = 'physical gun fire electric wind ice bless curse almighty'.split()

    def __init__(self, *values):
        super().__init__()
        for v in values:
            self[self._k[values.index(v)]] = v

    def __repr__(self):
        return "TypeDict(" + ', '.join(f"{k}={v}"for k, v in self.items()) + ')'


_severity = {
    "miniscule": 0.5,
    "light": 0.75,
    "medium": 1,
    "heavy": 1.5,
    "severe": 3,
    "colossal": 5
}


resistance = {'immune': 0.0, 'resist': 0.5, 'normal': 1.0, 'weak': 2.0, 'reflect': 0.5, 'absorb': -0.5}
_r = {'physical': 0, 'gun': 1, 'fire': 2, 'electric': 3, 'wind': 4, 'ice': 5, 'bless': 6, 'curse': 7, 'almighty': 8}
_res_tuple = collections.namedtuple("_res_tuple", "damage_dealt resistance")


class Resist(enum.Enum):
    immune = 0
    resist = 1
    normal = 2
    weak = 3
    reflect = 4
    absorb = 5


class BattleDemon:
    """The class for the new PvP system."""

    __slots__ = ("name", "_owner", "_hp", "_moves", "_strength", "_magic", "_endurance", "_agility", "_luck",
                 "_resistances")

    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self._owner = kwargs.get("owner")
        self._hp = kwargs.get("hp")
        self._moves = kwargs.get("moves")
        self._strength, self._magic, self._endurance, self._agility, self._luck = kwargs.get("stats")
        self._resistances = TypeDict(*kwargs.get("resistances"))
        # _resistances: {type: key} eg {'fire': 1, 'air': 3}
        # 0:            0x damage taken
        # 1:          0.5x damage taken
        # 2:            1x damage taken
        # 3:            2x damage taken
        # 4: Reflects 0.5x damage back on the attacker
        # 5:  Absorbs 0.5x damage to heal

    def __str__(self):
        return self.name

    @property
    def strength(self):
        """Returns an int of the demons Strength stat."""
        return self._strength

    @property
    def magic(self):
        """Returns an int of the demons Magic stat."""
        return self._magic

    @property
    def endurance(self):
        """Returns an int of the demons Endurance stat."""
        return self._endurance

    @property
    def agility(self):
        """Returns an int of the demons Agility stat."""
        return self._agility

    @property
    def luck(self):
        """Returns an int of the demons Luck stat."""
        return self._luck

    @property
    def owner(self):
        """Returns a Player object denoting the player this demon relates to."""
        return self._owner

    @property
    def hp(self):
        """Returns the total Hit Points remaining of the Demon.
        BattleDemon._hp but read only."""
        return self._hp

    def evade_chance(self, other):
        """Returns 100 + chance of evading a hit.
        This is affected by the Luck and Agility of
        (WIP) This will be affected"""
        bp = self._agility + self._luck
        ep = other.agility + other.luck
        return 100 - (max(bp, ep) - min(bp, ep))

    def try_evade(self, other):
        """Returns a bool whether you successfully evaded the attack.
        This is random, based on BattleDemon.evade_chance."""
        return random.randint(1, 100) > self.evade_chance(other)

    def is_fainted(self):
        """Returns a bool whether the demon has run out of HP."""
        return self._hp <= 0

    def resists(self, type_):
        """Returns a key denoting how the demon resists a type.
        Refer to L394 for a list of keys."""
        if type_ not in _r:
            raise ValueError("value not valid type")
        return Resist(self._resistances[type_])

    def resist_calc(self, type_):
        """Returns a float with a damage modifier"""
        if not isinstance(type_, Resist):
            raise TypeError("expected Resist enum, got {!r}".format(type_))
        return resistance[type_.name]

    def reflect_damage(self, amount):
        """Hmm"""
        self._hp -= amount

    def take_damage(self, demon, type_, severity):
        """Subtracts damage from the demons HP.
        This takes into account the demons endurance, type resistances and move severity.
        Returns a namedtuple with the total damage dealt, and the effect (resist, absorb etc)."""
        base = demon.strength - (self.endurance * .334)
        res = self.resists(type_)
        sevmod = _severity[severity]
        base *= sevmod
        mod = self.resist_calc(res)
        base = round(base * mod)
        base = base if base > 0 else 1
        # ^ This is to ensure all moves do at least 1 hitpoint of damage.
        if res is not Resist.reflect:
            self._hp -= base
        else:
            demon.reflect_damage(base)
        return _res_tuple(base, res)


Quest = collections.namedtuple("Quest", "qid find exp gold")
