from discord.ext.commands import Context

import asyncio


class EpicContext(Context):
    async def warn(self, message):
        msg = await super().send(message, delete_after=11)
        await msg.add_reaction(self.bot.tick)
        await msg.add_reaction(self.bot.cross)

        def warn_check(r, u):
            return str(r) in ("<:tickNo:490607198443929620>", "<:tickYes:490607182010777620>") and u == self.author

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=warn_check, timeout=10.0)
        except asyncio.TimeoutError:
            return False
        else:
            return str(reaction) == "<:tickYes:490607182010777620>"
