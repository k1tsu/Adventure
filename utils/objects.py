import humanize
from datetime import datetime, timedelta

import utils

import logging
maplog = logging.getLogger("Adventure.MapManager")
plylog = logging.getLogger("Adventure.PlayerManager")


class Map:
    __slots__ = ("id", "name", "nearby", "density")

    def __init__(self, *, map_id: int, name: str, density: int):
        self.id = map_id
        self.name = name
        self.nearby = set()
        self.density = density

    def _mini_repr(self):
        return f"<Map id={self.id} name={self.name}>"

    def __repr__(self):
        return f"<Map id={self.id} name='{self.name}' nearby={set(map(self.__class__._mini_repr, self.nearby))}>"

    def __str__(self):
        return self.name

    def __int__(self):
        return self.id

    def calculate_travel_to(self, other):
        # hours of travel
        if not isinstance(other, Map):
            raise ValueError("Must be a Map object.")
        return (self.density + other.density) // 1234


class Player:
    __slots__ = ("owner", "name", "_map", "_bot", "_next_map")

    def __init__(self, *, owner, name, bot):
        self._bot = bot
        self.owner = owner
        self.name = name
        self._map = self._bot.map_manager.get_map(0)
        self._next_map: Map = None

    def __repr__(self):
        return "<Player name='{0.name}' owner={0.owner!r} map={0.map!r}>".format(self)

    def __str__(self):
        return self.name

    @property
    def is_admin(self):
        return self.owner.id in self._bot.config.OWNERS

    @property
    def map(self):
        return self._map

    @map.setter
    def map(self, value):
        if isinstance(value, Map):
            self._map = value
        else:
            _map = self._bot.map_manager.get_map(value)
            if not _map:
                raise ValueError("Unknown map")
            self._map = _map

    async def is_travelling(self):
        return await self.travel_time() > 0

    async def update_travelling(self):
        if await self.is_travelling():
            return  # the TTL hasnt expired
        if not self._next_map:
            dest = self._bot.redis.execute("GET", f"next_map_{self.owner.id}")
        else:
            dest = self._next_map.id
        if not dest:
            return  # the player isnt travelling at all
        plylog.info("%s has returned from their adventure.", self.name)
        self._map = self._bot.map_manager.get_map(dest)
        await self._bot.redis.execute("DEL", f"next_map_{self.owner.id}")

    async def travel_time(self):
        return await self._bot.redis.execute("TTL", f"travelling_{self.owner.id}")

    async def travel_to(self, destination: Map):
        if await self.is_travelling():
            raise utils.AlreadyTravelling(self.name,
                                          humanize.naturaltime((datetime.now() + timedelta(
                                                          seconds=await self.travel_time()))))

        time = int(((datetime.now() + timedelta(
            hours=self.map.calculate_travel_to(destination))) - datetime.now()).total_seconds())
        self._next_map = destination
        plylog.info("%s is adventuring to %s and will return in %.0f hours.",
                    self.name, destination, self.map.calculate_travel_to(destination))
        x = await self._bot.redis.execute("SET", f"travelling_{self.owner.id}", str(time), "EX", str(time))
        await self._bot.redis.execute("SET", f"next_map_{self.owner.id}", str(destination.id))
        return round(self.map.calculate_travel_to(destination))

    async def save(self, *, cursor=None):
        q = """
INSERT INTO players
VALUES ($1, $2, $3)
ON CONFLICT (owner_id)
DO UPDATE
SET map_id = $3
WHERE players.owner_id = $1;
        """
        if not cursor:
            await self._bot.db.execute(q, self.owner.id, self.name, self._map.id)
        else:
            await cursor.execute(q, self.owner.id, self.name, self._map.id)

    async def delete(self, *, cursor=None):
        if not cursor:
            await self._bot.db.execute("DELETE FROM players WHERE owner_id=$1;", self.owner.id)
        else:
            await cursor.execute("DELETE FROM players WHERE owner_id=$1;", self.owner.id)
        self._bot.player_manager.players.remove(self)
        plylog.info("Player \"%s\" was deleted. (%s [%s])", self.name, self.owner, self.owner.id)
        del self
