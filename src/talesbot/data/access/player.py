from unicodedata import category
from discord import Member
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from talesbot import channels
from talesbot.config import known_handles
from .sequence import next_player

from ..schema import Player, Actor


async def create(session: Session, user: Member, handle: str):
    known_handle = known_handles.get(handle)
    if known_handle is None:
        return f'Failed: invalid starting handle "{handle}"'

    player = session.scalar(select(Player).where(Player.discord_id == user.id))
    if player is not None:
        return f"Error: Could not create player for member {user.id}, since they already have player_id {player.id}."

    next_player_index = next_player(session)

    guild_count = (
        session.scalar(
            select(func.count(Player.id)).where(Player.guild_id == user.guild.id)
        )
        or 0
    )

    category_index = 1 + (guild_count - 1) // 3

    actor = Actor(guild_id=user.guild.id)

    cmd_line_channel = await channels.create_personal_channel(
        user.guild,
        role,
        channels.get_cmd_line_name(new_player_id),
        new_player_id,
        category_index,
    )

    player = Player(
        discord_id=user.id,
        guild_id=user.guild.id,
        category=category_index,
        next_player_index=next_player_index,
    )
