import asyncio
import logging
import os

import discord
import uvicorn

from .logger import init_loggers

from .api import app
from .bot import TalesBot

TOKEN = os.getenv("DISCORD_TOKEN")


async def start_bot():
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


async def main() -> int:
    init_loggers()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(start_bot())
        tg.create_task(start_api())
