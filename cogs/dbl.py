import asyncio
import json
import logging

log = logging.getLogger("Adventure.cogs.dbl")
log.setLevel(logging.DEBUG)


async def update_dbl(bot):
    await bot.prepared.wait()
    while True:
        try:
            await bot.dbl_client.post_server_count()
        except Exception as e:
            log.critical("Failed to post server count to DiscordBotList.\n%s: %s", type(e).__name__, str(e))
        await asyncio.sleep(7200)


async def dbl_hook(bot):
    await bot.prepared.wait()
    channel = bot._redis.pubsub_channels[b"vote-channel"]
    ch = bot.get_channel(561390634863165450)
    print("init", channel, ch)
    while await channel.wait_message():
        try:
            payload = await channel.get_json(encoding='utf-8')
            print("recieved payload", payload)
        except json.decoder.JSONDecodeError:
            print("payload bad json")
            continue
        await ch.send(payload)


def setup(bot):
    log.debug("one")
    bot.dbl_task = bot.loop.create_task(update_dbl(bot))
    log.debug("two")
    bot.hook_task = bot.loop.create_task(dbl_hook(bot))
    log.debug("three")


def teardown(bot):
    try:
        bot.dbl_task.cancel()
    except asyncio.CancelledError:
        pass
    try:
        bot.hook_task.cancel()
    except asyncio.CancelledError:
        pass
