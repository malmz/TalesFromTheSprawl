import asyncio
import contextlib
import logging
import os

import discord
import uvicorn
import uvloop
from dotenv import load_dotenv

from .api import app
from .bot import TalesBot
from .logger import init_loggers


async def start_bot():
    TOKEN = os.getenv("DISCORD_TOKEN")
    exts = [
        "talesbot.handles",
        "talesbot.finances",
        "talesbot.admin",
        "talesbot.chats",
        "talesbot.shops",
        "talesbot.gm",
        "talesbot.artifacts",
    ]

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    async with TalesBot(intents=intents, inital_extensions=exts) as bot:
        await bot.start(TOKEN)


async def start_api():
    config = uvicorn.Config(app=app, port=5000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def start() -> int:
    async with asyncio.TaskGroup() as tg:
        # tg.create_task(start_bot())
        tg.create_task(start_api())


def main() -> int:
    load_dotenv()
    init_loggers()
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    with contextlib.suppress(KeyboardInterrupt):
        return asyncio.run(start())
