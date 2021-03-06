from .objects import *
from .formats import *
from .context import *
from .errors import *
from .paginator import *
from .djisktra import *
from .ipc import IPC


import asyncio
import functools

loop = asyncio.get_event_loop()


def async_executor():
    def outer(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            thing = functools.partial(func, *args, **kwargs)
            return loop.run_in_executor(None, thing)
        return inner
    return outer
