import asyncio
import logging

import discord
from discord.ext import commands

from . import data
from .config import EnvSettings

logger = logging.getLogger(__name__)


class TalesBot(commands.Bot):
    async def on_ready(self):
        logger.debug(f"Logged in as {self.user} (ID: {self.user.id})")

    async def setup_hook(self) -> None:
        await asyncio.gather(
            *(
                asyncio.create_task(self.load_extension(extension))
                for extension in extensions
            )
        )

    async def on_guild_available(self, guild: discord.Guild):
        print(f"Guild connected: {guild.name}({guild.id})")
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


extensions = [
    "talesbot.cogs.handles",
    "talesbot.cogs.finances",
    "talesbot.cogs.admin",
    "talesbot.cogs.chats",
    "talesbot.cogs.shops",
    "talesbot.cogs.gm",
    "talesbot.cogs.artifacts",
]


def main() -> int:
    logging.basicConfig(level=logging.DEBUG)
    env = EnvSettings()  # type: ignore

    data.create_tables()

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = TalesBot(intents=intents)  # type: ignore

    logger.debug("Starting bot...")
    bot.run(env.discord_token, reconnect=True)
    return 0
