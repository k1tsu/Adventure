import json


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
