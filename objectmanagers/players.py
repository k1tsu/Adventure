from utils import Player

import asyncio
import logging
log = logging.getLogger("Adventure.PlayerManager")


class PlayerManager:
    def __init__(self, bot):
        self.bot = bot
        self.players = set()
        self.unload_event = asyncio.Event()
        self.bot.unload_complete.append(self.unload_event)
        # log.debug("init")

    def fetch_players(self):
        return self.bot.db.fetch("SELECT * FROM players;")

    async def on_ready(self):
        # log.debug("on_ready")
        await self.bot.prepared.wait()
        # log.debug("wait complete")
        for owner_id, name, map_id in await self.fetch_players():
            player = Player(owner=self.bot.get_user(owner_id), name=name, bot=self.bot)
            player.map = map_id
            self.players.add(player)
            log.info("Player \"%s\" (%s) initialized at map \"%s\".", player.name, str(player.owner), player.map)

    async def on_logout(self):
        q = """
INSERT INTO players
VALUES ($1, $2, $3)
ON CONFLICT (owner_id)
DO UPDATE
SET map_id = $3
WHERE players.owner_id = $1;
        """
        async with self.bot.db.acquire() as cur:
            for player in self.players:
                await cur.execute(q, player.owner.id, player.name, player.map.id)
                log.info("Flushed player \"%s\" (%s).", player.name, player.owner)
        self.unload_event.set()


def setup(bot):
    bot.add_cog(PlayerManager(bot))
