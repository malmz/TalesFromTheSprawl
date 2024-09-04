import asyncio
import contextlib
import sys

import uvloop
from dotenv import load_dotenv

from . import main

load_dotenv()

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
with contextlib.suppress(KeyboardInterrupt):
    sys.exit(asyncio.run(main()))
