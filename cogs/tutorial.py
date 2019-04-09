"""
i dont like this module any more than you do
it was a pain to set up and i hate it
"""

import asyncio
import io
import random

import discord
from discord.ext.commands import Command

import blobs
import utils


def first_check(ctx):
    def check(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and m.content == f"{ctx.prefix}create"
    return check


def second_check(ctx):
    def check(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
    return check


def third_check(ctx):
    def check(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and m.content == f"{ctx.prefix}maps"
    return check


def fourth_check(ctx, rmsg):
    def check(r, u):
        return u.id == ctx.author.id and r.message.id == rmsg.id and str(r) == "\N{BLACK SQUARE FOR STOP}"
    return check


def fifth_check(ctx):
    def check(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and \
               m.content.lower() == f"{ctx.prefix}travel abel woods"
    return check


def sixth_check(ctx):
    def check(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and \
               m.content == f"{ctx.prefix}explore"
    return check


def seventh_check(ctx):
    def check(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and \
               m.content == f"{ctx.prefix}profile"
    return check


def eigth_check(ctx):
    def check(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and \
               m.content == f"{ctx.prefix}encounter"
    return check


def ninth_check(ctx):
    def check(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and \
               m.content == f"{ctx.prefix}compendium"
    return check


async def maps_(ctx, player):
    """Views all maps that you can travel to.
    This wont show maps that are not nearby."""
    pg = utils.EmbedPaginator()
    for _map in player.map.nearby:
        embed = discord.Embed(color=_map._raw['colour'], description=_map.description)
        embed.set_author(name=_map.name)
        embed.add_field(name="ID", value=str(_map.id))
        embed.add_field(name="Density", value=str(_map.density))
        pg.add_page(embed)
    inf = utils.EmbedInterface(ctx.bot, pg, ctx.author)
    await inf.send_to(ctx)
    return inf.message


async def encounter(ctx, player):
    em = ctx.bot.enemy_manager
    enemies = em.enemies_for(ctx.bot.map_manager.resolve_map("abel woods"))
    enemy = random.choice(enemies)
    exp = random.randint((enemy.tier ** 3) // 8, (enemy.tier ** 3) // 4) + 1
    gold = random.randint(enemy.tier * 2, enemy.tier * 6)
    player.exp += exp
    player.gold += gold
    await ctx.send(f"{blobs.BLOB_CHEER} You encountered **{enemy.name}** and defeated it!\n"
                   f"You gained **{exp}** experience points and **{gold}** coins!")
    return enemy


async def capture(ctx):
    em = ctx.bot.enemy_manager
    enemies = em.enemies_for(ctx.bot.map_manager.resolve_map("abel woods"))
    enemy = random.choice(enemies)
    await ctx.send(f"{blobs.BLOB_CHEER} You captured **{enemy.name}**!")
    return enemy


async def tutorial(ctx: utils.EpicContext):
    bot = ctx.bot
    if bot.player_manager.get_player(ctx.author):
        return await ctx.send("You already have a player! No need to run the tutorial!")
    if ctx.author.id in bot.in_tutorial:
        return
    bot.in_tutorial.append(ctx.author.id)

    await ctx.send("Hiya! I'm gonna run you through a tutorial on how to use this bot!")
    await asyncio.sleep(2)
    await ctx.send(f"First off, you'll need a player. You can achieve this by using `{ctx.prefix}create`.")
    await ctx.bot.wait_for("message", check=first_check(ctx))
    await ctx.send(f"{blobs.BLOB_O} What should the name be? (Name must be 32 characters or lower in length)")
    msg = await ctx.bot.wait_for("message", check=second_check(ctx))
    await ctx.send(f"{blobs.BLOB_PARTY} Success! \"{msg.clean_content}\" was sent to map #0 (Abel)")
    player = utils.Player(
        bot=bot,
        owner=ctx.author,
        name=msg.clean_content,
        created_at=msg.created_at
    )
    await asyncio.sleep(2)
    await ctx.send("Great! Now you have a player. Lets run through some basic commands.")
    await asyncio.sleep(2)
    await ctx.send(f"You aren't gonna get far without knowing where you can go. Try using `{ctx.prefix}maps` to view"
                   f" the current available maps.")
    await bot.wait_for("message", check=third_check(ctx))
    msg = await maps_(ctx, player)
    await ctx.send("Click \N{BLACK SQUARE FOR STOP} when you are done.")
    await bot.wait_for("reaction_add", check=fourth_check(ctx, msg))
    await ctx.send("Good. Now you know where you are, it's time to do some exploring.")
    await asyncio.sleep(2)
    await ctx.send(f"Let's head on over to the woods. We can explore around there.\nUse `{ctx.prefix}travel abel woods`"
                   f" to head over there.")
    await bot.wait_for("message", check=fifth_check(ctx))
    _map = bot.map_manager.resolve_map("abel woods")
    time = _map.calculate_travel_to(player)
    await ctx.send(f"{blobs.BLOB_SALUTE} {player.name} is now travelling to Abel Woods and "
                   f"will arrive in {time*60:.0f} minutes.")
    await asyncio.sleep(2)
    await ctx.send(f"Since this is a tutorial, you don't actually have to wait {time*60:.0f} minutes."
                   f" I'll speed you up.")
    await asyncio.sleep(2)
    player.map = _map
    await ctx.send(f"{blobs.BLOB_PARTY} {player.name} has arrived at Abel Woods!")
    await asyncio.sleep(2)
    await ctx.send(f"Now that we have arrived, it's time to explore the area. Use `{ctx.prefix}explore` to begin.")
    await bot.wait_for("message", check=sixth_check(ctx))
    time = _map.calculate_explore()
    await ctx.send(f"{blobs.BLOB_SALUTE} {player.name} is now exploring Abel Woods and"
                   f" will finish in {time*60:.0f} minutes.")
    await asyncio.sleep(2)
    await ctx.send("Exploring tends to take a lot longer than travelling."
                   " I'll speed you up again for the sake of this tutorial.")
    player.explored_maps.append(player.map)
    await asyncio.sleep(2)
    await ctx.send(f"{blobs.BLOB_PARTY} {player.name} has finished exploring Abel Woods!")
    await asyncio.sleep(2)
    await ctx.send(f"Side note, you can use `{ctx.prefix}profile` to view your current profile.")
    await bot.wait_for("message", check=seventh_check(ctx))
    await ctx.trigger_typing()
    async with bot.session.get(str(ctx.author.avatar_url_as(format="png", size=256))) as get:
        avy = io.BytesIO(await get.read())
    profile = await bot.player_manager.profile_for(avy, player)
    file = discord.File(profile, "profile.png")
    await ctx.send(file=file)
    await asyncio.sleep(2)
    await ctx.send("Hmm, you seem a little low on exp there. Outside the tutorial,"
                   " travelling / exploring gives you quite a lot of experience. "
                   "I'll give you a little exp buff for now.")
    await asyncio.sleep(2)
    player.exp += 1729
    await ctx.send(f"{blobs.BLOB_PARTY} {player.name} has levelled to tier 12!")
    await asyncio.sleep(2)
    await ctx.send("Now that you are buffed up, it's time to fight some enemies!")
    await asyncio.sleep(2)
    await ctx.send(f"Let's search for something! Use `{ctx.prefix}encounter` to search for an enemy.")
    await bot.wait_for("message", check=eigth_check(ctx))
    await encounter(ctx, player)
    await asyncio.sleep(2)
    await ctx.send("Good job! After defeating an enemy, you'll be awarded with Experience and Coins.")
    await asyncio.sleep(2)
    await ctx.send("As you get more exp, the enemies you are able to defeat increases.")
    await asyncio.sleep(2)
    await ctx.send("There is one more mechanic I can show you, which is the `capturing` mechanic.")
    await asyncio.sleep(2)
    await ctx.send("The `capturing` mechanic is vital, as filling the `compendium` is the goal of your adventure.")
    await asyncio.sleep(2)
    await ctx.send(f"Try using `{ctx.prefix}encounter` again, this time you'll be prompted to capture the enemy.")
    await bot.wait_for("message", check=eigth_check(ctx))
    enemy = await capture(ctx)
    await asyncio.sleep(2)
    await ctx.send(f"Sweet, you captured the {enemy.name}. Now if you use the command `{ctx.prefix}compendium`, "
                   f"it'll show it's name in a table.")
    await bot.wait_for("message", check=ninth_check(ctx))
    comp = player.compendium
    comp.bits[enemy.id-1] = 1
    render = comp.format()
    await ctx.send(f"```\n{render}\n```")
    await asyncio.sleep(2)
    await ctx.send("And that's pretty much everything! Since your player is a tutorial player, I'll have to delete it.")
    await asyncio.sleep(2)
    await ctx.send("Try to remember everything that happened in this tutorial, and you should be fine.")
    await asyncio.sleep(2)
    await ctx.send("Good luck on your Adventure!")
    bot.in_tutorial.remove(ctx.author.id)
    del player


tut = Command(tutorial)


def setup(bot):
    bot.add_command(tut)


def teardown(bot):
    bot.remove_command("tutorial")
