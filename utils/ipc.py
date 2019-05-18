import json


class IPC:
    def __init__(self, bot):
        self.bot = bot
        # noinspection PyProtectedMember
        self.redis = bot._redis
        self.loop = bot.loop
        self.recv = self.loop.create_task(self.receiver())
        self.recv_channel = None

    def parser(self, **data):
        return getattr(self, data['op'])(*data['args'], **data['kwargs'])

    async def receiver(self):
        await self.bot.wait_until_ready()
        self.recv_channel = await self.redis.execute_pubsub("SUBSCRIBE", "IPC-webserver")
        while await self.recv_channel.wait_message():
            recv = await self.recv_channel.get_json(encoding='utf-8')
            find = await self.parser(**recv)
            await self.send(find)

    async def get_user(self, userid):
        user = self.bot.get_user(userid)
        if not user:
            return await self.bot.http.get_user(userid)
        return {
            "id": str(user.id),
            "avatar": user.avatar,
            "name": user.name,
            "discriminator": user.discriminator
        }

    async def send(self, data):
        await self.bot.redis("PUBLISH", "IPC-adventure", json.dumps(data))
