import logging

from discord import Interaction, app_commands
from discord.ext import commands

from talesbot import handles, players
from talesbot.database import SessionM, transaction

from ..errors import MissingHandleError
from ..utils import fmt_handle, fmt_money

logger = logging.getLogger(__name__)


class FinanceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        description="Send Nuyen (¥) to another handle."
        " The money will be sent from your current handle."
    )
    async def pay(self, interaction: Interaction, target: str, amount: int):
        await interaction.response.defer(ephemeral=True)
        async with SessionM() as session:
            actor_id = players.fetch_player_id(str(interaction.user.id))
            active_handle = handles.get_active_handle_id(actor_id)
            if active_handle is None:
                raise MissingHandleError(actor_id)

            await transaction.transfer(
                session,
                sender_handle=active_handle,
                receiver_handle=target,
                amount=amount,
            )
        await interaction.followup.send(
            f"Successfully transferred {fmt_money(amount)}"
            f"from {fmt_handle(active_handle)} to {fmt_handle(target)}",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(FinanceCog(bot))
