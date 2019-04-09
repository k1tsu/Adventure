import asyncio
import json
import pprint

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
    js = await request.json()
    await g.redis.execute("LPUSH", g.channel, json.dumps(js))
    pprint.pprint(js)
    print(repr(request.headers))
    # await g.redis.execute("PUBLISH", g.channel, json.dumps(await request.json()))
    return web.Response(status=200)


async def run():
    g.redis = await asyncio.wait_for(aioredis.create_pool(config.REDIS_ADDRESS, password=config.REDIS_PASS), timeout=10)
    app = web.Application()
    app.add_routes(routes)
    print("init")
    await web._run_app(app, port=80)


async def exit():
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
