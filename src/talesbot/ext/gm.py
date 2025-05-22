import logging

import discord
from discord import Interaction, app_commands, utils
from discord.app_commands.errors import MissingRole, NoPrivateMessage
from discord.ext import commands

from talesbot import (
    gm,
    handles,
    player_setup,
    scenarios,
)
from talesbot.database import SessionM, artifact

from ..errors import ReportError

logger = logging.getLogger(__name__)


@app_commands.guild_only()
class GmCog(commands.GroupCog, group_name="gm"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def interaction_check(self, interaction: Interaction) -> bool:
        """Check for gm role"""
        if isinstance(interaction.user, discord.User):
            raise NoPrivateMessage()

        role = utils.get(interaction.user.roles, name=gm.role_name)

        if role is None:
            raise MissingRole(gm.role_name)
        return True

    @app_commands.command(
        description="Add a player's handle before they join the server",
    )
    async def add_known_handle(self, interaction: Interaction, handle_id: str):
        player_setup.add_known_handle(handle_id)
        await interaction.response.send_message(
            (
                f"Added entry for {handle_id}. Please update its contents manually "
                "by editing the file"
            ),
            ephemeral=True,
        )

    scenario_g = app_commands.Group(name="scenario", description="Manage scenarios")

    @scenario_g.command(name="run", description="Run a scenario")
    async def run_scenario(self, interaction: Interaction, name: str):
        report = await scenarios.run_scenario(name)
        if report is None:
            report = "Command finished without any output"
        await interaction.response.send_message(report, ephemeral=True)

    @scenario_g.command(name="create", description="Create a basic scenario")
    async def create_scenario(self, interaction: Interaction, name: str):
        report = await scenarios.create_scenario(name)
        if report is None:
            report = "Command ended without any output"
        await interaction.response.send_message(report, ephemeral=True)

    artifact_g = app_commands.Group(name="artifact", description="Manage artifacts")

    @artifact_g.command(
        name="create",
        description="Create an artifact.",
    )
    async def create_artifact(
        self,
        interaction: Interaction,
        name: str,
        content: str,
        password: str | None = None,
        announcment: str | None = None,
        page: int | None = None,
    ):
        async with SessionM() as session:
            try:
                _a, page = await artifact.create(
                    session,
                    name,
                    content,
                    password=password,
                    announcement=announcment,
                    page=page,
                )
            except Exception as e:
                raise ReportError("Failed to create artifact") from e

            await interaction.response.send_message(
                f"Set page {page} on artifact {name}", ephemeral=True
            )

    @artifact_g.command(
        name="list",
        description="List all artifacts.",
    )
    async def list_artifact(self, interaction: Interaction):
        async with SessionM() as session:
            artifact_list = await artifact.list(session)
            body = "\n".join([a.name for a in artifact_list])
            await interaction.response.send_message(
                f"Registerd artifacts\n```{body}```", ephemeral=True
            )

    @app_commands.command(description="Reinitialise the GM context and handles.")
    async def init(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        async with handles.semaphore():
            await gm.init(clear_all=True)
        await interaction.followup.send("Done.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GmCog(bot))
