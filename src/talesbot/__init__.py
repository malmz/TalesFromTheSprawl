import asyncio
import contextlib
import os

import discord
import uvicorn
import uvloop
from discord.ext import commands
from dotenv import load_dotenv

from .api import app
from .bot import TalesBot
from .config import config_dir
from .logger import init_loggers

config_folders = [
    "actors",
    "artifacts",
    "chats",
    "finances",
    "groups",
    "handles",
    "logs",
    "players",
    "scenarios",
    "shops",
]


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

    async with TalesBot(
        commands.when_mentioned, intents=intents, inital_extensions=exts
    ) as bot:
        await bot.start(TOKEN)


async def start_api():
    host = os.getenv("HOST") or "127.0.0.1"
    port = int(os.getenv("PORT") or "5000")
    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def start() -> int:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(start_bot())
        tg.create_task(start_api())


def main() -> int:
    load_dotenv()

    for folder in config_folders:
        os.makedirs(config_dir / folder, exist_ok=True)

    init_loggers()
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    with contextlib.suppress(KeyboardInterrupt):
        return asyncio.run(start())
