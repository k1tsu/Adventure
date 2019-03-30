import asyncio
import logging

log = logging.getLogger("Adventure.cogs.dbl")
log.setLevel(logging.DEBUG)


async def update_dbl(bot):
    while True:
        try:
            await bot.dbl_client.post_server_count()
        except Exception as e:
            log.critical("Failed to post server count to DiscordBotList.\n%s: %s", type(e).__name__, str(e))
        await asyncio.sleep(7200)


def setup(bot):
    bot.dbl_task = bot.loop.create_task(update_dbl(bot))


def teardown(bot):
    try:
        bot.dbl_task.cancel()
    except asyncio.CancelledError:
        pass
