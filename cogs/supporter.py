import io

from PIL import Image
import discord
from discord.ext import commands

import blobs
import utils


class Supporter(commands.Cog):
    """
    Commands that may only be used by supporters.
    You can become a supporter by donating any amount here:
    <https://www.patreon.com/xua_yraili>.
    """
    def __init__(self, bot):
        self.bot = bot
        self.dump: discord.TextChannel = None

    async def cog_check(self, ctx):
        if ctx.author in await self.bot.get_supporters():
            return True
        raise utils.NotSupporter

    @commands.command()
    async def customreset(self, ctx):
        """Resets your custom background and colour to the defaults."""
        await self.bot.db.execute("UPDATE supporters SET cstmbg=NULL, textcol=16777215 WHERE userid=$1;", ctx.author.id)
        await ctx.send(f"Done! {blobs.BLOB_THUMB}")

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def custombg(self, ctx, *, url):
        """Upload an image to use as a custom background.

        Only supporter:tm:s may use this command.
        The image will be resized to 499x370."""
        await ctx.trigger_typing()
        async with self.bot.session.get(url) as get:
            if get.headers['Content-Type'] != 'image/png':
                return await ctx.send(f"{blobs.BLOB_ARMSCROSSED} You must supply a valid PNG image.\n"
                                      f"Type given was `{get.headers['Content-Type']}`, instead of `image/png`")
            if int(get.headers['Content-Length']) > 8388608:
                return await ctx.send("Image is too large! Cannot be bigger than 8 MB")
            image = io.BytesIO(await get.read())
        res = await self.resize(image)
        url = await self.dump_image(res)
        await self.bot.db.execute("UPDATE supporters SET cstmbg=$2 WHERE userid=$1;", ctx.author.id, url)
        await ctx.send(f"{blobs.BLOB_CHEER} Finished!")

    @commands.command(aliases=['textcolor', 'textcolour', 'txtcol'])
    async def textcol(self, ctx, *, colour: discord.Colour):
        """Allows you to change the text colour in \*profile

        Only supporters may use this command."""
        await self.bot.db.execute("UPDATE supporters SET textcol=$1 WHERE userid=$2;", colour.value, ctx.author.id)
        await ctx.send(embed=discord.Embed(color=colour, title="Done!"))

    async def dump_image(self, image):
        file = discord.File(image, "dump.png")
        msg = await self.dump.send(file=file)
        att = msg.attachments[0]
        return att.url

    @utils.async_executor()
    def resize(self, image: io.BytesIO):
        pre = Image.open(image)
        mid = pre.convert("RGBA")
        pos = mid.resize((499, 370))
        buf = io.BytesIO()
        pos.save(buf, "png")
        buf.seek(0)
        return buf

    @commands.Cog.listener()
    async def on_ready(self):
        self.dump = self.bot.get_channel(561392448232751106)


def setup(bot):
    bot.add_cog(Supporter(bot))
