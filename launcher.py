import asyncio
from asyncio.subprocess import PIPE
import sys
import traceback

import logging

ANSI_RESET = "\33[0m"

ANSI_COLOURS = {
    "WARNING": "\33[93m",
    "DEBUG": "\33[96m",
    "ERROR": "\33[91m",
    "CRITICAL": "\33[95m"
}


class ColouredFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("[%(asctime)s %(name)s/%(levelname)s]: %(message)s", "%H:%M:%S")

    def format(self, record: logging.LogRecord):
        levelname = record.levelname
        record.levelname = levelname[:4]
        msg = super().format(record)
        if levelname == "INFO":
            return msg
        return ANSI_COLOURS[levelname] + msg + ANSI_RESET


handler = logging.StreamHandler()
handler.setFormatter(ColouredFormatter())

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s %(name)s/%(levelname)s]: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("logs/adventure.log", "w", encoding='UTF-8'),
        handler
    ]
)
try:
    logging.getLogger("discord.client").disabled = True
    logging.getLogger("discord.http").disabled = True
    logging.getLogger("discord.gateway").disabled = True
    logging.getLogger("discord.state").disabled = True
    logging.getLogger("asyncio").disabled = True
    logging.getLogger("websockets.protocol").disabled = True
    logging.getLogger("aioredis").disabled = True
finally:
    pass


log = logging.getLogger("Adventure.Launcher")


if sys.platform == "win32":
    py = "py"
    asyncio.set_event_loop(asyncio.ProactorEventLoop())
else:
    py = "python"


async def stderr(stream):
    async for line in stream:
        log.error(line.decode().rstrip("\n"))


async def stdout(stream):
    async for line in stream:
        log.info(line.decode().rstrip("\n"))


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
