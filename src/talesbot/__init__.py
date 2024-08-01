import discord
from discord.ext import commands

from .conf import ClientExtension, Config, exts, set_exts

# from . import channels
from .db import Player
from .logger import init_bot_logger
from talesbot import db

intents = discord.Intents.default()
bot = commands.Bot(intents=intents)


class TalesBot(commands.Bot):
	async def on_ready():
		print(f"Bot connected as {bot.user.name}")

	async def on_guild_available(guild: discord.Guild):
		pass


def main() -> int:
	db.create_tables()

	client_extensions = ClientExtension()

	print("Starting bot...")
	bot.run(client_extensions.env_settings.discord_token)
