import asyncio
import logging
from typing import cast

from discord import Interaction, Member, app_commands
from discord.ext import commands

from talesbot import common, handles, players, server
from talesbot.database import SessionM, artifact

from ..errors import ArtifactNotFoundError
from ..ui.artifact import ArtifactView

logger = logging.getLogger(__name__)


class ArtifactsCog(commands.Cog):
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
        self, interaction: Interaction, name: str, password: str | None = None
    ):
        await interaction.response.defer(ephemeral=True)
        member = cast(Member, interaction.user)
        async with SessionM() as session:
            a = await artifact.access(session, name, password)

            if a is None:
                await self.log_connect_attempt(member, name, password)
                raise ArtifactNotFoundError(name)

            await asyncio.gather(
                self.log_connect_attempt(member, name, password, a.announcement),
                interaction.followup.send(
                    content=a.content[0].content, view=ArtifactView(a), ephemeral=True
                ),
            )

    async def log_connect_attempt(
        self,
        user: Member,
        name: str,
        password: str | None,
        announcement: str | None = None,
    ):
        player_id = players.get_player_id(str(user.id))
        handle = (
            handles.get_active_handle(player_id).handle_id
            if player_id is not None
            else f"{user.name}(unregisterd)"
        )
        password_info = f"password {password}" if password else "no password"
        log_report = f"**{handle}** requested {name} using {password_info}"
        if announcement:
            log_report += f"\n{announcement}"
        await server.send_message_to_all(common.gm_announcements_name, log_report)


async def setup(bot: commands.Bot):
    await bot.add_cog(ArtifactsCog(bot))
