import pkgutil
from interactions import Client, Intents, listen
from interactions.api.events import MessageCreate, Ready

from .conf import ClientExtension, Config, exts, set_exts

# from . import channels
from .db import Player
from .logger import init_bot_logger


logger = init_bot_logger()

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


""" @listen
async def process_messages(event: MessageCreate):
    if event.message.author.bot or channels.is_offline_channel(event.message.channel):
        return

    player_name = Player.get(Player.discord_id == event.message.author.id).player_id """

print("Starting bot...")

for extension_name in pkgutil.iter_modules(["talesbot.exts"], "talesbot.exts."):
    print(f"Loading extension {extension_name.name}")
    bot.load_extension(extension_name.name)

bot.start(client_extensions.config.token)
