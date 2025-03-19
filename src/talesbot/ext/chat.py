import asyncio
from collections.abc import Generator
from typing import cast

from discord import Guild, Interaction, Member, Message, TextChannel, app_commands
from discord.abc import GuildChannel
from discord.ext.commands import Bot, Cog
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from talesbot import channels, common, players
from ..broadcaster import Broadcaster

from ..database import SessionM
from ..database.models import Chat, ChatMember, ChatMessage, Handle
from ..errors import NotRegisterdError, ReportError
from ..game import is_2party_chat_possible


class ChatCog(Cog):

    bot: Bot
    broadcaster: Broadcaster

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.broadcaster = Broadcaster()

    @app_commands.command()
    async def chat(self, interaction: Interaction, handle: str):
        await interaction.response.defer(ephemeral=True)
        handle = handle.lower()
        user = cast(Member, interaction.user)
        async with SessionM() as session, session.begin():
            player = await players.get_player(session, user.id)
            if player is None:
                raise NotRegisterdError(user)

            init_handle = player.active_handle
            other_handle = await session.scalar(
                select(Handle).where(Handle.name == handle)
            )
            if other_handle is None:
                raise ReportError(f"Recipient {handle} does not exist")
            if not is_2party_chat_possible(init_handle.name, other_handle.name):
                raise ReportError(
                    "**NETWORK OFFLINE**\n[OFF: you can still chat with GMs]"
                )

            if init_handle.actor_id == other_handle.actor_id:
                raise ReportError("You cannot chat with yourself")

            chat_name = _chat_name([init_handle.name, other_handle.name])

            chat = await session.scalar(select(Chat).where(Chat.name == chat_name))
            if chat is None:
                init_member = ChatMember(
                    channel_name=f"{init_handle.name}_to_{other_handle.name}",
                    handle=init_handle,
                )
                other_member = ChatMember(
                    channel_name=f"{other_handle.name}_to_{init_handle.name}",
                    handle=other_handle,
                )
                chat = Chat(
                    name=chat_name, is_active=True, members=[init_member, other_member]
                )
                session.add(chat)

    @Cog.listener()
    async def on_ready(self):
        for chan in self.chat_channels():
            if isinstance(chan, TextChannel):


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
                    player.active_handle.name if player is not None else "anon"
                )
                await self.broadcast_message(channel.name, sender_name, message)

        elif channels.is_chat_channel(channel):
            await message.delete()
            async with SessionM() as session, session.begin():
                chat_member = await session.scalar(
                    select(ChatMember)
                    .where(ChatMember.channel_name == channel.name)
                    .options(
                        selectinload(ChatMember.handle, ChatMember.chat).selectinload(
                            Chat.members
                        )
                    )
                )
                if chat_member is None:
                    raise RuntimeError(f"chat channel {channel.name} not db")

                chat = chat_member.chat

                chan_names = [m.channel_name for m in chat.members]

                await self.broadcast_message(
                    chan_names, chat_member.handle.name, message
                )

                chat_message = ChatMessage(
                    content=message.content, chat=chat, sender=chat_member.handle
                )
                session.add(chat_message)

    def chat_channels(self, guild: Guild | None = None):
        if guild is None:
            for guild in self.bot.guilds:
                for cat in guild.categories:
                    if cat.name == channels.is_chat_channel(cat):
                        yield from cat.channels
        else:
            for cat in guild.categories:
                if cat.name == common.chats_categories:
                    yield from cat.channels

    async def broadcast_message(
        self,
        channel_names: str | list[str],
        sender_name: str,
        message: Message,
        category_name: str | None = None,
    ):
        if isinstance(channel_names, str):
            channel_names = [channel_names]

        chans = self._find_channels(channel_names, category_name)
        files = [await a.to_file() for a in message.attachments]
        async with asyncio.TaskGroup() as tg:
            for c in chans:
                tg.create_task(
                    c.send(
                        f"<{sender_name}> {message.content}",
                        files=files,
                    )
                )

    def _find_channels(
        self, channel_names: list[str], category_name: str | None = None
    ) -> Generator[TextChannel]:
        source = (
            self._get_all_category_channels(category_name)
            if category_name is not None
            else self.bot.get_all_channels()
        )
        for c in source:
            if isinstance(c, TextChannel) and c.name in channel_names:
                yield c

    def _get_all_category_channels(self, category_name: str) -> Generator[GuildChannel]:
        for guild in self.bot.guilds:
            for ca in guild.categories:
                if ca.name == category_name:
                    yield from ca.channels


def _chat_name(handles: list[str]) -> str:
    return "_".join(sorted(handles))


async def setup(bot: Bot):
    await bot.add_cog(ChatCog(bot))
