import logging
from typing import cast

from discord import Guild, Interaction, Member, PermissionOverwrite, Role, app_commands
from discord.ext import commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from talesbot import common, config, handles, players
from talesbot.access import group

from ..bot import TalesBot
from ..database import SessionM
from ..database.models import Group, Player
from ..errors import InvalidStartingHandleError
from ..known_handles import read_known_handles
from ..ui.register import RegisterView

logger = logging.getLogger(__name__)


class PlayerCog(commands.Cog):
    def __init__(self, bot: TalesBot):
        self.bot = bot

    @app_commands.command(
        description=(
            "Claim a handle and join the game. "
            "Only for players who have not yet joined."
        ),
    )
    @app_commands.guild_only()
    @app_commands.checks.has_role(common.new_player_role_name)
    async def join(self, interaction: Interaction, handle: str):
        await interaction.response.defer(ephemeral=True)
        member = cast(Member, interaction.user)  # Safe because of "guild_only"

        if handle == "handle" or handle == "<handle>":
            await interaction.followup.send(
                'You must say which handle is yours! Example: "/join shadow_weaver"',
                ephemeral=True,
            )
            return

        if handle != handle.lower():
            handle = handle.lower()
            await interaction.followup.send(
                f"Handles are always lowercase, using {handle}", ephemeral=True
            )

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

        await interaction.followup.send(
            "Success! Now have a look at all your new channels 🥳",
            ephemeral=True,
        )

    async def create_player(self, session: AsyncSession, member: Member, handle: str):
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

    async def create_group(self, session: AsyncSession, name: str):
        group = await session.scalar(select(Group).where(Group.name == name))
        if group is None:
            group = Group(name=name)
            session.add(group)
            await session.refresh(group)

            await _create_channels(
                list(self.bot.guilds), common.groups_category_name, name
            )

        return group


async def _create_channels(
    guilds: list[Guild],
    category: str,
    name: str,
    overrides: dict[Role | Member, PermissionOverwrite] | None = None,
):
    for guild in guilds:
        for cat in guild.categories:
            if cat.name == category:
                if overrides is not None:
                    await cat.create_text_channel(name, overrides=overrides)
                else:
                    await cat.create_text_channel(name)


async def setup(bot: TalesBot):
    bot.add_view(RegisterView())
    await bot.add_cog(PlayerCog(bot))
