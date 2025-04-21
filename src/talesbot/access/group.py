import discord
from discord import Guild
from discord.ext import commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from talesbot import channels, groups

from ..database.models import Group


class GroupService:
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def ensure(
        self, session: AsyncSession, guilds: list[Guild], name: str
    ) -> Group:
        group = await session.scalar(select(Group).where(Group.name == name))
        if group is None:
            group = Group(name=name)
            session.add(group)

        for guild in self.bot.guilds:
            group_cat = discord.utils.find(
                lambda c: channels.is_group_category(c), guild.categories
            )
            await group_cat.create_text_channel(name)

        return group
