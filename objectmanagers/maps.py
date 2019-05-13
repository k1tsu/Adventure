# -> Builtin modules
import collections
import logging
import os
from typing import List

# -> Pip packages
import discord
from discord.ext import commands
from discord.utils import find

# -> Local files
import blobs
import utils

log = logging.getLogger("Adventure.MapManager")

try:
    import ujson as json
except ImportError:
    log.warning("Couldn't import ujson. Using regular json instead.")
    import json


class MapManager(commands.Cog, name="Maps"):
    """Makes sure the maps are working properly, and some other stuff."""
    __slots__ = ("bot", "_maps")
    _ignore = (-1, 696969)

    def __init__(self, bot):
        self.bot = bot
        self._maps: List[utils.Map] = []
        self.prepare_maps()
        self._graph = utils.Graph()
        for map in self.maps:
            for m in map.nearby:
                self._graph.add_map(map.id, m.id, map.density + m.density)
        self.dj = utils.djisktra

    def __repr__(self):
        return "<MapManager total: {0}>".format(len(self._maps))

    def cog_unload(self):
        del self._maps[:]

    # -- Commands -- #

    @commands.group(name="maps", invoke_without_command=True)
    async def maps_(self, ctx):
        """Views all maps that you can travel to.
        This wont show maps that are not nearby."""
        player = self.bot.player_manager.get_player(ctx.author)
        if not player:
            return await ctx.invoke(self.all_)
        pg = utils.EmbedPaginator()
        for _map in player.map.nearby:
            embed = discord.Embed(color=_map._raw['colour'], description=_map.description)
            embed.set_author(name=_map.name)
            embed.add_field(name="ID", value=str(_map.id))
            embed.add_field(name="Density", value=str(_map.density))
            pg.add_page(embed)
        inf = utils.EmbedInterface(self.bot, pg, ctx.author)
        await inf.send_to(ctx)

    @maps_.command(name="all")
    async def all_(self, ctx):
        """View all maps, regardless if they are nearby."""
        pg = utils.EmbedPaginator()
        for _map in self.maps:
            if _map.id in self._ignore:
                continue
            embed = discord.Embed(color=_map._raw['colour'], description=_map.description)
            embed.set_author(name=_map.name + (' (Safe)' if _map.is_safe else ''))
            embed.add_field(name="ID", value=str(_map.id))
            embed.add_field(name="Density", value=str(_map.density))
            embed.add_field(name="Nearby Maps", value="`" + "`, `".join(map(str, _map.nearby)) + "`", inline=False)
            pg.add_page(embed)
        inf = utils.EmbedInterface(self.bot, pg, ctx.author)
        await inf.send_to(ctx)

    @maps_.command(ignore_extra=False)
    async def explored(self, ctx):
        """Views all the maps you have explored."""
        player = self.bot.player_manager.get_player(ctx.author)
        if not player:
            return await ctx.send(f"You don't have a player! {blobs.BLOB_PLSNO} Create one with `{ctx.prefix}create`!")
        pg = utils.EmbedPaginator()
        for _map in player.explored_maps:
            embed = discord.Embed(colour=_map._raw['colour'], description=_map.description)
            embed.set_author(name=_map.name + (' (Safe)' if _map.is_safe else ''))
            embed.add_field(name="ID", value=str(_map.id))
            embed.add_field(name="Density", value=str(_map.density))
            embed.add_field(name="Nearby Maps", value="`" + "`, `".join(map(str, _map.nearby)) + "`", inline=False)
            pg.add_page(embed)
        inf = utils.EmbedInterface(self.bot, pg, ctx.author)
        await inf.send_to(ctx)

    @commands.command(aliases=['qt'])
    @commands.cooldown(2, 3600, commands.BucketType.user)
    async def quicktravel(self, ctx, *, map):
        """Quickly travels your player to a map.
        This is quite expensive, so beware."""
        player = self.bot.player_manager.get_player(ctx.author)
        if not player:
            raise utils.NoPlayer()
        if await player.is_travelling() or await player.is_exploring():
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"{blobs.BLOB_ARMSCROSSED} You are busy!"
                                  f" Wait until you are idling before you use this command.")
        map = self.resolve_map(map)
        if not map:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"Unknown map. See `{ctx.prefix}maps explored` to view your explored maps.")
        if not player.has_explored(map):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"{blobs.BLOB_ANGERY} You haven't explored {map}!")
        start = player.map
        path = self.dj(self._graph, start.id, map.id)
        for mid in path:
            mm = self.get_map(mid)
            if not player.has_explored(mm):
                return await ctx.send(f"{blobs.BLOB_ARMSCROSSED} You must explore {mm} first!")
        cost = sum(self.get_map(p).density for p in path)
        if player.gold < cost:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"{blobs.BLOB_SAD} You are too poor!"
                                  f" You need **{cost} G**, but only have **{player.gold} G**.")
        if not await ctx.warn(f"{blobs.BLOB_THINK} This will cost **{cost} G**,"
                              f" and you have **{player.gold} G**. Are you sure?"):
            ctx.command.reset_cooldown(ctx)
            return
        player.map = map
        player.gold -= cost
        await ctx.send(f"{blobs.BLOB_SALUTE} {player.name} quick travelled to {map}!")

    @quicktravel.error
    async def quicktravel_error(self, ctx, exc):
        if isinstance(exc, commands.CommandOnCooldown):
            await ctx.send("You can only quick travel twice every hour!")
        else:
            await self.bot.get_cog("Handler").on_command_error(ctx, exc, enf=True)

    # -- MapManager stuff -- #

    @property
    def maps(self):
        return self._maps

    def resolve_map(self, item):
        if isinstance(item, int):
            return self.get_map(item)
        elif isinstance(item, str) and item.lstrip("-").isdigit():
            return self.get_map(int(item))
        elif isinstance(item, bytes) and item.lstrip(b"-").isdigit():
            return self.get_map(int(item))
        elif isinstance(item, str):
            return find(lambda m: m.name.lower() == item.lower(), self.maps)
        elif isinstance(item, utils.Map):
            return item
        elif item is None:
            return None
        log.debug(f"{item} {type(item)}")
        raise RuntimeError("what")

    def _add_map(self, **data):
        _id = int(data["id"])
        if self.get_map(_id):
            log.error("Map with id \"%s\" already exists. (%s)", _id, self.get_map(_id))
            return
        _map = utils.Map(**data)
        # self._add_map_nearby(_map, *list(map(self.get_map, data['nearby'])))
        _map._nearby = data['nearby']
        self._maps.append(_map)

    def walk_paths(self, start):
        seen = [start.id]

        def get_nearby(map_id):
            l = filter(lambda x: map_id in x.nearby, self._maps)
            return sorted(l, key=lambda x: x.density)

        l = collections.deque([[start]])
        while True:
            try:
                x = l.popleft()
                yield x
                seen.append(x[-1].id)
                for y in get_nearby(x[-1].id):
                    if y.id not in seen:
                        l.append([*x, y])
            except IndexError:
                raise StopIteration

    @staticmethod
    def _add_map_nearby(map1: utils.Map, *maps: utils.Map):
        for _map in maps:
            if map1 == _map or (_map is None or map1 is None) or (map1 in _map.nearby or _map in map1.nearby):
                continue
            map1.nearby.append(_map)
            _map.nearby.append(map1)

    def get_map(self, map_id: int):
        return find(lambda m: m.id == map_id, self._maps)

    def prepare_maps(self):
        for _map in sorted(os.listdir("maps"), key=lambda i: i.lower()):
            with open("maps/" + _map) as f:
                try:
                    _json = json.load(f)
                    self._add_map(**_json)
                except Exception as e:
                    log.error("Map %s is malformed. [%s: %s]", _map, type(e).__name__, str(e))

        for _map in self.maps:
            self._add_map_nearby(_map, *list(map(self.get_map, _map._nearby)))
            log.info("Prepared map %s.", _map)


def setup(bot):
    cog = MapManager(bot)
    bot.add_cog(cog)
    # bot.map_manager = cog

