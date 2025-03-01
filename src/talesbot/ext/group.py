import logging

import discord
from discord import Message, Permissions, TextChannel
from discord.ext.commands import Bot, Cog
from sqlalchemy import select

from talesbot import common
from talesbot.broadcaster import Broadcaster

from ..database import SessionM
from ..database.models import Group

logger = logging.getLogger(__name__)


class GroupCog(Cog):
    bot: Bot
    broadcaster: Broadcaster

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        async with SessionM() as session, session.begin():
            groups = await session.scalars(select(Group))

            group_channels: dict[str, list[TextChannel]] = dict()
            for chan in self.group_channels():
                if isinstance(chan, TextChannel):
                    group_channels.setdefault(chan.name, []).append(chan)

            for group in groups:
                chans = group_channels.get(group.name)
                if chans is not None:
                    for chan in chans:
                        role = discord.utils.find(
                            lambda x, g=group: x.name == g.role_name, chan.guild.roles
                        )
                        if role is None:
                            role = await chan.guild.create_role(
                                name=group.role_name, permissions=Permissions()
                            )
                        chan.per

                        self.broadcaster.add_channel(group.name, chan)
                else:
                    logger.error(f"Missing channels for group {group.name}")

    @Cog.listener()
    async def on_message(self, message: Message):
        pass

    def group_channels(self):
        for guild in self.bot.guilds:
            for cat in guild.categories:
                if cat.name == common.groups_category_name:
                    yield from cat.channels
