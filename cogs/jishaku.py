from datetime import datetime

from jishaku import cog
from jishaku.exception_handling import *

import blobs


class AltReplReactor(ReplResponseReactor):

    async def __aenter__(self):
        self.handle = self.loop.create_task(do_after_sleep(1, attempt_add_reaction, self.message, blobs.BLOB_WOBBLE))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.handle:
            self.handle.cancel()
        if not exc_val:
            await attempt_add_reaction(self.message, blobs.BLOB_TICK)
            return
        self.raised = True
        if isinstance(exc_val, (asyncio.TimeoutError, subprocess.TimeoutExpired)):
            await attempt_add_reaction(self.message, "\N{ALARM CLOCK}")
        elif isinstance(exc_val, SyntaxError):
            await attempt_add_reaction(self.message, blobs.BLOB_CROSS)
        else:
            await attempt_add_reaction(self.message, blobs.BLOB_CROSS)


cog.JISHAKU_RETAIN = True
cog.ReplResponseReactor = AltReplReactor


class Jishaku(cog.Jishaku):
    def __init__(self, bot):
        super().__init__(bot)
        self.start_time = datetime.utcnow()


def setup(bot):
    bot.add_cog(Jishaku(bot))
