import logging
from typing import cast

from discord import Interaction, Member, app_commands
from discord.ext import commands

from talesbot import common, handles, players

from ..bot import TalesBot
from ..database import SessionM
from ..ui.register import RegisterView

logger = logging.getLogger(__name__)


class RegisterCog(commands.Cog):
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

        async with SessionM() as session:
            _player = await self.bot.players.create_player(session, member, handle)
            await interaction.followup.send(
                "Success! Now have a look at all your new channels 🥳",
                ephemeral=True,
            )


async def setup(bot: TalesBot):
    bot.add_view(RegisterView())
    await bot.add_cog(RegisterCog(bot))
