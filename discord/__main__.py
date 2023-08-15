from interactions import Client, Intents, listen
from dotenv import load_dotenv
import os


class Config:
    def __init__(self):
        self.token = os.getenv("DISCORD_TOKEN")
        self.application_id = os.getenv("APPLICATION_ID")
        self.guild_id = os.getenv("GUILD_ID")
        self.gm_role = os.getenv("GM_ROLE_NAME")


load_dotenv()
config = Config()

bot = Client(intents=Intents.DEFAULT)


@listen
async def on_ready():
    print(f"Bot connected as {bot.user.tag}")


bot.load_extension("artifacts")
bot.start(config.token)
