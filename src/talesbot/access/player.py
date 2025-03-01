import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from talesbot.access import group

from ..database.models import Player
from ..errors import InvalidStartingHandleError
from ..known_handles import read_known_handles


async def get(session: AsyncSession, discord_id: int) -> Player | None:
    return await session.scalar(
        select(Player).where(Player.discord_id == discord_id).options(joinedload())
    )


async def create(session: AsyncSession, member: discord.Member, handle: str):
    known_handles = read_known_handles()
    if handle not in known_handles:
        raise InvalidStartingHandleError(handle)

    known_handle = known_handles[handle]

    groups = [await group.ensure(session, g) for g in known_handle.groups]

    player = Player(
        name=handle,
        guild_id=member.guild.id,
        discord_id=member.id,
        channel_id=0,
        groups=groups,
    )
    session.add(player)
