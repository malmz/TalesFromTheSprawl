"""
This module handles the creation and execution of in-game artifacts, which are items
that can be accessed through logging in with codes.
"""

from discord import Interaction, app_commands
from discord.ext import commands

from .. import common, handles, players, server
from ..data.access import artifact

# TODO: reinitialise?


class ArtifactsCog(commands.Cog, name="network"):
    """Commands for connecting to devices and accessing files."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        description="Connect to device or remote server. Aliases: /login, /access",
    )
    async def connect(
        self, interaction: Interaction, code: str, password: str | None = None
    ):
        await self.do_connect(interaction, code, password)

    @app_commands.command(
        description="Connect to device or remote server. Same as /connect.",
    )
    async def login(
        self, interaction: Interaction, code: str, password: str | None = None
    ):
        await self.do_connect(interaction, code, password)

    @app_commands.command(
        description="Connect to device or remote server. Same as /connect.",
    )
    async def access(
        self, interaction: Interaction, code: str, password: str | None = None
    ):
        await self.do_connect(interaction, code, password)

    async def do_connect(
        self, interaction: Interaction, code: str, password: str | None = None
    ):
        await interaction.response.defer(ephemeral=True)
        (report, announcement) = artifact.access(code, password)
        await self.log_connect_attempt(
            interaction.user.id, code, password, announcement
        )
        if report is not None:
            await interaction.followup.send(report, ephemeral=True)
        else:
            await interaction.followup.send("Unable to connect.", ephemeral=True)

    async def log_connect_attempt(
        self,
        user_id: int,
        code: str,
        password: str | None,
        announcement: str | None = None,
    ):
        try:
            player_id = players.get_player_id(user_id)
            handle = handles.get_active_handle(player_id)
            password_info = f"password {password}" if password else "no password"
            log_report = (
                f"**{handle.handle_id}** requested {code} using {password_info}"
            )
            if announcement:
                log_report += f"\n{announcement}"
            await server.send_message_to_all(common.gm_announcements_name, log_report)
        except:
            print("Failed to log connect attempt")


async def setup(bot: commands.Bot):
    await bot.add_cog(ArtifactsCog(bot))
