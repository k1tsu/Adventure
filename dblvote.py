import asyncio
import json

from aiohttp import web
import aioredis

import config


class Global:
    pass


g = Global()
g.redis: aioredis.ConnectionsPool = None
g.channel = "vote-channel"


routes = web.RouteTableDef()


@routes.get('/')
async def home(request):
    return web.Response(status=200, text="Online!")


@routes.post('/vote')
async def vote(request):
    await g.redis.execute("PUBLISH", g.channel, json.dumps(await request.json()))
    return web.Response(status=200)


async def run():
    await g.redis.execute_pubsub("SUBSCRIBE", g.channel)
    app = web.Application()
    app.add_routes(routes)
    print("init")
    await web._run_app(app, port=8080)


async def exit():
    await g.redis.execute_pubsub("UNSUBSCRIBE", g.channel)
    g.redis.close()
    await g.redis.wait_closed()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        loop.run_until_complete(exit())
    finally:
        loop.stop()
        loop.close()
