import discord

from .conf import ClientExtension, Config, exts, set_exts

# from . import channels
from .db import Player
from .logger import init_bot_logger
from talesbot import db

intents = discord.Intents.default()
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Bot connected as {client.user.name}")


def main() -> int:
    db.create_tables()

    client_extensions = ClientExtension()

    print("Starting bot...")
    client.run(client_extensions.env_settings.discord_token)
