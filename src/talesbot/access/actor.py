from discord import Guild, TextChannel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Actor, player_actor_seq


async def _next_player_id(session: AsyncSession) -> int:
    next_id: int = await session.scalar(player_actor_seq)
    return next_id


async def create_player(
    session: AsyncSession,
    guild: Guild,
    finance_channel: TextChannel,
    chat_channel: TextChannel,
) -> Actor:
    player_id = await _next_player_id(session)

    actor = Actor(
        name="u" + str(player_id),
        role_name=str(player_id),
        guild_id=guild.id,
        finance_channel_id=finance_channel.id,
        chat_channel_id=chat_channel.id,
    )

    session.add(actor)

    return actor
