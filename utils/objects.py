class Map:
    __slots__ = ("id", "name", "nearby")

    def __init__(self, *, map_id, name):
        self.id = map_id
        self.name = name
        self.nearby = set()

    def _mini_repr(self):
        return f"<Map id={self.id} name={self.name}>"

    def __repr__(self):
        return f"<Map id={self.id} name={self.name} nearby={set(map(self.__class__._mini_repr, self.nearby))}>"

    def __str__(self):
        return self.name

    def __int__(self):
        return self.id


class Player:
    __slots__ = ("owner", "name", "_map", "_bot")

    def __init__(self, *, owner, name, bot):
        self._bot = bot
        self.owner = owner
        self.name = name
        self._map = self._bot.map_manager.get_map(0)

    def __repr__(self):
        return "<Player name={0.name} owner={0.owner} map={0.map}>".format(self)

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

    async def save(self):
        q = """
INSERT INTO players
VALUES ($1, $2, $3)
ON CONFLICT (owner_id)
DO UPDATE
SET map_id = $3
WHERE players.owner_id = $1;
        """
        await self._bot.db.execute(q, self.owner.id, self.name, self._map.id)
