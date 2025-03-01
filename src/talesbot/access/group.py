from discord import Guild
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Group


async def ensure(session: AsyncSession, guilds: list[Guild], name: str) -> Group:
    group = await session.scalar(select(Group).where(Group.name == name))
    if group is None:
        group = Group(name=name)
        session.add(group)
        for guild in guilds:
            for cat in guild.by_category():
                

    return group
