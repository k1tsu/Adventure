# -> Builtin modules
import asyncio
import enum
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


class Map:
    __slots__ = ("id", "name", "nearby", "_nearby", "density", "_raw", "description")

    def __init__(self, **kwg):
        self._raw = kwg.copy()
        self.id = kwg.get("id")
        self.name = kwg.get("name")
        self.nearby = list()
        self.density = kwg.get("density")
        self.description = kwg.get("description")
        self._nearby = []

    def __repr__(self):
        return f"<Map id={self.id} name='{self.name}'>"

    def __eq__(self, other):
        return isinstance(other, type(self)) and other.id == self.id

    def __str__(self):
        return self.name

    def __int__(self):
        return self.id

    def calculate_travel_to(self, other) -> float:
        if not isinstance(other, Map):
            raise ValueError("Must be a Map object.")
        return (self.density + other.density) / 1234

    def calculate_explore(self) -> float:
        return (self.density * 1234) / (1000 ** 2)

    def travel_exp(self, map) -> int:
        if not isinstance(map, self.__class__):
            raise ValueError("'map' argument must be Map")
        time = map.calculate_travel_to(self) * 10
        return math.floor(time / 3)

    def explore_exp(self) -> int:
        return math.floor((self.calculate_explore() * 10) / 3)


class Player:

    def __init__(self, **kwg):
        self._bot = kwg.get("bot")
        self.owner = kwg.get("owner")
        self.name = kwg.get("name")
        self._map = self._bot.map_manager.get_map(0)
        self._next_map = None
        self.exp = kwg.get("exp", 0)
        self._next_level = self.level + 1
        self.created_at = kwg.get("created_at")
        self._explored_maps = kwg.get("explored", [self._bot.map_manager.get_map(0)])
        self.status = kwg.get("status", Status.idle)

    def __repr__(self):
        return "<Player name='{0.name}' owner={0.owner!r} exp={0.exp}>".format(self)

    def __str__(self):
        return self.name

    @property
    def level(self) -> int:
        return math.floor(self.exp ** .334)

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
            await ctx.send("{} {} has arrived at {}!".format(blobs.BLOB_PARTY, self, self.map))
        elif await self.update_exploring():
            await ctx.send("{} {} has finished exploring {}!".format(blobs.BLOB_PARTY, self, self.map))
        if self.update_level():
            await ctx.send("{} {} levelled to tier **{}**!".format(blobs.BLOB_PARTY, self, self.level))

    def update_level(self) -> bool:
        if self.level >= self._next_level:
            self._next_level = self.level + 1
            return True
        return False

    async def update_travelling(self) -> bool:
        await asyncio.sleep(1)
        if await self.is_travelling():
            if self._next_map is None:
                dest = await self._bot.redis("GET", f"next_map_{self.owner.id}")
                self._next_map = self._bot.map_manager.get_map(dest)
            return False  # the TTL hasnt expired
        if self._next_map is None:
            dest = await self._bot.redis("GET", f"next_map_{self.owner.id}")
        else:
            dest = self._next_map.id
        if dest is None:
            return False  # the player isnt travelling at all
        self.exp += self.map.travel_exp(self._next_map)
        self._next_map = None
        plylog.info("%s has arrived at their location.", self.name)
        self.map = dest
        await self._bot.redis("DEL", f"next_map_{self.owner.id}")
        await self._bot.redis("SET", f"status_{self.owner.id}", "0")
        self.status = Status.idle
        return True

    async def update_exploring(self) -> bool:
        await asyncio.sleep(1)
        if await self.is_exploring():
            return False
        if self.status == Status.exploring or await self._bot.redis("GET", f"status_{self.owner.id}") == 2:
            plylog.info("%s has finished exploring %s.", self.name, self.map)
            await self._bot.redis("SET", f"status_{self.owner.id}", "0")
            self.status = Status.idle
            self.exp += self.map.explore_exp()
            return True

    async def travel_time(self) -> int:
        if not self.map:
            self.map = await self._bot.redis("GET", f"next_map_{self.owner.id}")
        return await self._bot.redis("TTL", f"travelling_{self.owner.id}")

    async def explore_time(self) -> int:
        return await self._bot.redis("TTL", f"exploring_{self.owner.id}")

    # -- Real functions -- #

    async def travel_to(self, destination: Map):
        if await self.is_travelling():
            raise utils.AlreadyTravelling(self.name,
                                          humanize.naturaltime((datetime.now() + timedelta(
                                                          seconds=await self.travel_time()))))
        elif await self.is_exploring():
            raise utils.AlreadyTravelling(self.name,
                                          humanize.naturaltime((datetime.now() + timedelta(
                                                          seconds=await self.explore_time()))))
        time = int(((datetime.now() + timedelta(hours=self.map.calculate_travel_to(destination))) - datetime.now()
                    ).total_seconds())
        self._next_map = destination
        plylog.info("%s is adventuring to %s and will finish in %.2f hours.",
                    self.name, destination, self.map.calculate_travel_to(destination))
        await self._bot.redis("SET", f"travelling_{self.owner.id}", str(time), "EX", str(time))
        await self._bot.redis("SET", f"next_map_{self.owner.id}", str(destination.id))
        await self._bot.redis("SET", f"status_{self.owner.id}", "1")
        self.status = Status.travelling

    async def explore(self):
        if await self.is_travelling():
            raise utils.AlreadyTravelling(self.name,
                                          humanize.naturaltime((datetime.now() + timedelta(
                                              seconds=await self.travel_time()))))
        elif await self.is_exploring():
            raise utils.AlreadyTravelling(self.name,
                                          humanize.naturaltime((datetime.now() + timedelta(
                                              seconds=await self.explore_time()))))
        if self.map in self._explored_maps:
            raise utils.AlreadyExplored(self.map)
        time = int(((datetime.now() + timedelta(hours=self.map.calculate_explore())) - datetime.now()).total_seconds())
        plylog.info("%s is exploring %s and will finish in %.2f hours.",
                    self.name, self.map, self.map.calculate_explore())
        await self._bot.redis("SET", f"exploring_{self.owner.id}", str(time), "EX", str(time))
        await self._bot.redis("SET", f"status_{self.owner.id}", "2")
        self.status = Status.exploring
        self._explored_maps.append(self.map)

    async def save(self, *, cursor=None):
        q = """
INSERT INTO players (owner_id, name, map_id, created_at, explored, exp)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (owner_id)
DO UPDATE
SET name = $2, map_id = $3, explored = $5, exp = $6
WHERE players.owner_id = $1;
        """
        if not cursor:
            await self._bot.db.execute(q, self.owner.id, self.name, self._map.id, self.created_at,
                                       list(map(operator.attrgetter("id"), self.explored_maps)), self.exp)
        else:
            await cursor.execute(q, self.owner.id, self.name, self._map.id, self.created_at,
                                 list(map(operator.attrgetter("id"), self.explored_maps)), self.exp)

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
    def __init__(self, *, id: int, name: str, cost: float):
        self.id = id
        self.name = name
        self.cost = cost
