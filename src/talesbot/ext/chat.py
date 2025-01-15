from typing import cast

from discord import Message
from discord.abc import GuildChannel
from discord.ext.commands import Bot, Cog

from talesbot import channels


class ChatCog(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot or channels.is_offline_channel(
            cast(GuildChannel, message.channel)
        ):
            return

        async with database.SessionM() as session:
            p = await player.get(session, message.author.id)

            player_name = p.actor.name if p is not None else "[unregistered]"

            channel_name = cast(str, message.channel.name)  # type: ignore

            cmd_logger.info(
                f"{message.author.id} : {player_name} : "
                f"{channel_name} : {message.content}"  # type: ignore
            )


async def setup(bot: Bot):
    await bot.add_cog(ChatCog(bot))
