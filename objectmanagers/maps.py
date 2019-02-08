from discord.utils import get as find
import ujson
import os

import utils

import logging

log = logging.getLogger("Adventure.MapManager")


class MapManager:
    __slots__ = ("bot", "_maps")

    def __init__(self, bot):
        self.bot = bot
        self._maps = []
        self.prepare_maps()

    def __unload(self):
        del self._maps[:]

    @property
    def maps(self):
        return self._maps

    def _add_map(self, **data):
        _id = int(data.pop("id"))
        if self.get_map(_id):
            log.error("Map with id \"%s\" already exists. (%s)", _id, self.get_map(_id))
            return
        name = data.pop("name")
        near = list(map(self.get_map, data.pop("nearby")))
        _map = utils.Map(map_id=_id, name=name)
        self._add_map_nearby(_map, *near)
        self._maps.append(_map)
        if data:
            for item in data.keys():
                log.warning("Unused key \"%s\" in map \"%s\".", item, name)

    @staticmethod
    def _add_map_nearby(*maps: utils.Map):
        for _map in maps:
            for _map2 in maps:
                if _map == _map2 or (_map or _map2):
                    continue
                # log.debug("%s", repr(_map2))
                _map.nearby.add(_map2)
            # log.debug("%s", repr(_map))

    def get_map(self, map_id: int):
        return find(self._maps, id=int(map_id))

    def prepare_maps(self):
        for _map in os.listdir("maps"):
            with open("maps/" + _map) as f:
                try:
                    json = ujson.load(f)
                    self._add_map(**json)
                    log.info("Prepared map %s.", _map)
                except Exception as e:
                    log.error("Map %s is malformed. [%s: %s]", _map, type(e).__name__, str(e))


def setup(bot):
    bot.add_cog(MapManager(bot))
