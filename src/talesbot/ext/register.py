import logging
from typing import cast

from discord import Interaction, Member, app_commands
from discord.ext import commands

from talesbot import common, handles, players

from ..ui.register import RegisterView

logger = logging.getLogger(__name__)


class RegisterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
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
        else:
            async with handles.semaphore():
                # TODO give player some sort of warning about using lower-case only
                handle_id = handle.lower()
                report = await players.create_player(member, handle_id)
            if report is not None:
                await interaction.followup.send(
                    (
                        f'Failed: invalid starting handle "{handle_id}" '
                        "(or handle is already taken)."
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "Success! Now have a look at all your new channels 🥳",
                    ephemeral=True,
                )


async def setup(bot: commands.Bot):
    bot.add_view(RegisterView())
    await bot.add_cog(RegisterCog(bot))
