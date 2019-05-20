import json
import textwrap

from contextlib import redirect_stdout
import io

from utils import format_exception

from discord import HTTPException, NotFound


class IPC:
    def __init__(self, bot):
        self.bot = bot
        self.redis = None
        self.loop = bot.loop
        self.recv = self.loop.create_task(self.receiver())
        self.recv_channel = None

    def __repr__(self):
        return "<IPC {0.recv}>".format(self)

    def parser(self, **data):
        return getattr(self, data['op'])(*data['args'], **data['kwargs'])

    async def receiver(self):
        await self.bot.prepared.wait()
        # noinspection PyProtectedMember
        self.redis = self.bot._redis
        await self.redis.execute_pubsub("SUBSCRIBE", "IPC-webserver")
        self.recv_channel = self.redis.pubsub_channels['IPC-webserver']
        while await self.recv_channel.wait_message():
            recv = await self.recv_channel.get_json(encoding='utf-8')
            find = await self.parser(**recv)
            await self.send(find)
            
    def abort(self, code, reason):
        return {"error": code, "reason": reason}

    async def send(self, data):
        await self.bot.redis("PUBLISH", "IPC-adventure", json.dumps(data))

    # OPs

    async def get_user(self, userid):
        user = self.bot.get_user(userid)
        if not user:
            try:
                return await self.bot.http.get_user(userid)
            except NotFound:
                return self.abort(404, 'not found')
            except HTTPException as exc:
                return self.abort(exc.code, exc.response)
        return {
            "id": str(user.id),
            "avatar": user.avatar,
            "name": user.name,
            "discriminator": user.discriminator
        }

    async def eval(self, *, body):
        env = {"bot": self.bot,
               "redis": self.redis,
               "ipc": self}

        to = f"async def func():\n{textwrap.indent(body, '    ')}"

        try:
            exec(to, env)
        except Exception as e:
            return {"error": format_exception(e)}

        func = env['func']
        stdout = io.StringIO()

        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            return {"error": format_exception(e)}
        return {"body": ret}


