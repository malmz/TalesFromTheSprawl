from interactions import Client, Intents, listen
from interactions.api.events import MessageCreate
from dotenv import load_dotenv
import os

# from . import channels
from .db import Player
from .logger import init_bot_logger


class Config:
    def __init__(self):
        self.token = os.getenv("DISCORD_TOKEN")
        self.application_id = os.getenv("APPLICATION_ID")
        self.guild_id = os.getenv("GUILD_ID")
        self.gm_role = os.getenv("GM_ROLE_NAME")


load_dotenv()
config = Config()
logger = init_bot_logger()

bot = Client(intents=Intents.DEFAULT, logger=logger)


@listen
async def on_ready(event):
    print(f"Bot connected as {bot.user.tag}")


""" @listen
async def process_messages(event: MessageCreate):
    if event.message.author.bot or channels.is_offline_channel(event.message.channel):
        return

    player_name = Player.get(Player.discord_id == event.message.author.id).player_id """

print("Starting bot...")

# bot.load_extension("artifacts")
bot.start(config.token)
