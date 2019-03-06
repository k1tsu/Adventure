import asyncio
from asyncio.subprocess import PIPE
import sys
import traceback

if sys.platform == "win32":
    py = "py"
    asyncio.set_event_loop(asyncio.ProactorEventLoop())
else:
    py = "python3"


async def stderr(stream):
    async for line in stream:
        print("[stderr] " + line.decode().rstrip("\n"))


async def stdout(stream):
    async for line in stream:
        print(line.decode().rstrip("\n"))


loop = asyncio.get_event_loop()


def silent(*things):
    for thing in things:
        try:
            thing()
        except:
            pass


async def main():
    proc = await asyncio.create_subprocess_shell(py + " -m pip install -Ur requirements.txt",
                                                 stdout=PIPE, stderr=PIPE)
    out = loop.create_task(stdout(proc.stdout))
    err = loop.create_task(stderr(proc.stderr))

    await proc.wait()

    silent(out.cancel, err.cancel)


try:
    loop.run_until_complete(main())
except KeyboardInterrupt:
    pass
except Exception:
    traceback.print_exc()
finally:
    loop.stop()
    loop.close()

asyncio.set_event_loop(asyncio.new_event_loop())

from main import Adventure

Adventure().run()
