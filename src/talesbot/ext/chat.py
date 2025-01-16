import asyncio
from typing import cast

from discord import Message, TextChannel
from discord.abc import GuildChannel
from discord.ext.commands import Bot, Cog
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from talesbot import channels, players

from ..database import SessionM
from ..database.models import Chat, ChatMember


class ChatCog(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        channel = cast(GuildChannel, message.channel)
        if message.author.bot or channels.is_offline_channel(channel):
            return

        if channels.is_anonymous_channel(channel):
            await message.delete()
            await self.broadcast_message(channel.name, "anon", message)

        elif channels.is_pseudonymous_channel(channel):
            await message.delete()
            async with SessionM() as session:
                player = await players.get_player(session, message.author.id)
                sender_name = (
                    player.actor.active_handle.name if player is not None else "anon"
                )
                await self.broadcast_message(channel.name, sender_name, message)

        elif channels.is_chat_channel(channel):
            await message.delete()
            async with SessionM() as session:
                chat_member = session.scalar(
                    select(ChatMember)
                    .where(ChatMember.channel_name == channel.name)
                    .options(joinedload())
                )

    async def broadcast_message(
        self, channel_name: str, sender_name: str, message: Message
    ):
        chans = [
            c
            for c in self.bot.get_all_channels()
            if c.name == channel_name and isinstance(c, TextChannel)
        ]
        files = [await a.to_file() for a in message.attachments]
        async with asyncio.TaskGroup() as tg:
            for c in chans:
                tg.create_task(
                    c.send(
                        f"<{sender_name}> {message.content}",
                        files=files,
                        reference=message.reference,  # type: ignore
                    )
                )


async def setup(bot: Bot):
    await bot.add_cog(ChatCog(bot))
