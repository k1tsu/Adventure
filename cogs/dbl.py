import asyncio
import json
import logging
import random

import discord

import blobs

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
    key = "vote-channel"
    ch = bot.get_channel(561390634863165450)
    pm = bot.player_manager
    log.debug("init %s %s", key, ch)
    while True:
        try:
            with await bot._redis as pool:
                key, stuff = await pool.execute("BLPOP", key, "0")
            payload = json.loads(stuff)
            log.debug("recieved payload %s", payload)
        except IndexError as e:
            log.warning("bad payload recieved\n%s", e)
            continue
        except json.decoder.JSONDecodeError as e:
            log.warning("bad payload recieved\n%s\n%s", stuff, e)
            continue
        user = bot.get_user(int(payload['user']))
        if not user:
            continue
        await ch.send(f"{user.mention} ({user} {user.id}) voted for Adventure!")
        player = pm.get_player(user)
        if player:
            embed = discord.Embed(colour=discord.Colour(11059565))
            embed.set_author(name="Thanks for voting!", icon_url=bot.user.avatar_url_as(format="png", size=32))
            if not payload['isWeekend']:
                exp = random.randint(player.exp // 16, player.exp // 4)
                gold = random.randint(player.gold // 2, player.gold)
            else:
                exp = random.randint(player.exp // 8, player.exp // 2)
                gold = random.randint(player.gold, player.gold * 2)
                embed.set_footer(text="Since you voted on the weekend, you gained bonus points!")
            player.exp += exp
            player.gold += gold
            embed.description = (f"As a thank you gift, you've been awarded with\n"
                                 f"**{exp}** Experience Points and **{gold}** Coins!")
        else:
            embed = discord.Embed(colour=discord.Colour(11059565))
            embed.set_author(name="Thanks for voting!", icon_url=bot.user.avatar_url_as(format="png", size=32))
            embed.description = (f"Unfortunately, you don't have a player! {blobs.BLOB_PLSNO}\n"
                                 f"If you like, you can create one with `*create`.\n\n"
                                 f"(I don't listen to DMs, so youll need to invite me to a guild.)")
        try:
            await user.send("")
        except discord.Forbidden:
            continue
        except discord.HTTPException:
            pass
        await user.send(embed=embed)


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
