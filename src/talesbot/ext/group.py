import logging

from discord import Guild, Message, TextChannel
from discord.abc import GuildChannel
from discord.ext.commands import Bot, Cog
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from talesbot import channels, common
from talesbot.broadcaster import Broadcaster

from ..database import SessionM
from ..database.models import Group, Player

logger = logging.getLogger(__name__)


class GroupCog(Cog):
    """Group Cog handles group channels

    Keeps a list of group channels and mirrors messages between them
    """

    bot: Bot
    broadcaster: Broadcaster

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.broadcaster = Broadcaster()

    @Cog.listener()
    async def on_ready(self):
        for chan in self.group_channels():
            if isinstance(chan, TextChannel):
                self.broadcaster.add_channel(chan.name, chan)

        async with SessionM() as session:
            groups = await session.scalars(select(Group))
            group_names = {g.name for g in groups}
            channel_names = {
                c.name for c in self.group_channels() if isinstance(c, TextChannel)
            }

            for g in group_names.difference(channel_names):
                logger.warning(f"Missing channels for group {g}")

            for c in channel_names.difference(group_names):
                logger.warning(f"Dangling group channel {c}")

    @Cog.listener()
    async def on_guild_channel_create(self, channel: GuildChannel):
        if isinstance(channel, TextChannel) and channels.is_group_channel(channel):
            self.broadcaster.add_channel(channel.name, channel)

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel):
        if isinstance(channel, TextChannel) and channels.is_group_channel(channel):
            self.broadcaster.remove_channel(channel.name, channel)

    @Cog.listener()
    async def on_guild_channel_update(self, before: GuildChannel, after: GuildChannel):
        # If channel is renamed
        if before.name == after.name and before.category_id == after.category_id:
            pass

        if isinstance(before, TextChannel) and channels.is_group_channel(before):
            self.broadcaster.remove_channel(before.name, before)

        if isinstance(after, TextChannel) and channels.is_group_channel(after):
            self.broadcaster.add_channel(after.name, after)

    @Cog.listener()
    async def on_guild_available(self, guild: Guild):
        logger.info(f"Scanning guild {guild.name} for group channels")
        for chan in self.group_channels(guild):
            if isinstance(chan, TextChannel):
                self.broadcaster.add_channel(chan.name, chan)

        async with SessionM() as session:
            groups = await session.scalars(select(Group))
            group_names = {g.name for g in groups}
            channel_names = {
                c.name for c in self.group_channels(guild) if isinstance(c, TextChannel)
            }

            for g in group_names.difference(channel_names):
                logger.warning(f"Missing channels for group {g} in guild {guild.name}")

            for c in channel_names.difference(group_names):
                logger.warning(f"Dangling group channel {c} in guild {guild.name}")

    @Cog.listener()
    async def on_guild_unavailable(self, guild: Guild):
        logger.info(f"Disconnecting group channels for guild {guild.name}")
        self.broadcaster.remove_guild(guild)

    @Cog.listener()
    async def on_message(self, message: Message):
        if (
            not message.author.bot
            and isinstance(message.channel, TextChannel)
            and channels.is_group_channel(message.channel)
        ):
            await message.delete()

            async with SessionM() as session:
                player = await session.scalar(
                    select(Player)
                    .where(Player.discord_id == message.author.id)
                    .options(joinedload())
                )

                sender = "anon"
                if player is not None:
                    sender = player.active_handle.name

                await self.broadcaster.broadcast(message.channel.name, sender, message)

    def group_channels(self, guild: Guild | None = None):
        if guild is None:
            for guild in self.bot.guilds:
                for cat in guild.categories:
                    if cat.name == common.groups_category_name:
                        yield from cat.channels
        else:
            for cat in guild.categories:
                if cat.name == common.groups_category_name:
                    yield from cat.channels


async def setup(bot: Bot):
    await bot.add_cog(GroupCog(bot))
