from discord import Member
from discord.ext import commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from talesbot.access import group

from ..database import SessionM
from ..database.models import Player
from ..errors import InvalidStartingHandleError, ReportError
from ..known_handles import read_known_handles


class PlayerService:
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.group_service = GroupService()

    async def get(self, session: AsyncSession, discord_id: int) -> Player | None:
        return await session.scalar(
            select(Player).where(Player.discord_id == discord_id).options(joinedload())
        )

    async def register(self, session: AsyncSession, member: Member, handle: str):
        if handle == "handle" or handle == "<handle>":
            raise ReportError(
                'You must say which handle is yours! Example: "/join shadow_weaver"'
            )

        if handle != handle.lower():
            handle = handle.lower()
            raise ReportError(f"Handles are always lowercase, using {handle}")

        async with SessionM() as session, session.begin():
            known_handles = read_known_handles()
            if handle not in known_handles:
                raise InvalidStartingHandleError(handle)

            known_handle = known_handles[handle]

            groups = [
                await group.ensure(session, list(self.bot.guilds), g)
                for g in known_handle.groups
            ]

            player = Player(
                name=handle,
                guild_id=member.guild.id,
                discord_id=member.id,
                channel_id=0,
                groups=groups,
            )
            session.add(player)

    async def create(self, session: AsyncSession, member: Member, handle: str):
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


async def get(session: AsyncSession, discord_id: int) -> Player | None:
    return await session.scalar(
        select(Player).where(Player.discord_id == discord_id).options(joinedload())
    )


async def create(session: AsyncSession, member: Member, handle: str):
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
