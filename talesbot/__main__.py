import pkgutil
from interactions import Client, Intents, listen
from interactions.api.events import MessageCreate, Ready

from .conf import ClientExtension, Config, exts, set_exts

# from . import channels
from .db import Player
from .logger import init_bot_logger
from talesbot import db


logger = init_bot_logger()
db.create_tables()

client_extensions = ClientExtension()

bot = Client(
    intents=Intents.GUILDS
    | Intents.GUILD_MESSAGES
    | Intents.GUILD_WEBHOOKS
    | Intents.MESSAGE_CONTENT,
    logger=logger,
)

set_exts(bot, client_extensions)


@listen()
async def on_ready(event: Ready):
    meta = exts(bot)
    print(f"Bot connected as {bot.user.tag}, owner: {bot.owner}")
    await meta.impersonator.setup(bot)


print("Starting bot...")

bot.load_extension("interactions.ext.debug_extension")
bot.load_extension("interactions.ext.jurigged")
bot.load_extensions("talesbot/exts")

bot.start(client_extensions.env_settings.discord_token)
