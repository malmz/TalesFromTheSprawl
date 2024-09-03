from discord import Interaction, app_commands
from discord.ext import commands

from ..shops import order_product_from_command


class ShopCog(commands.Cog, name="shop"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(description="Order a product from a shop")
    async def order(self, interaction: Interaction, product: str, shop: str):
        await interaction.response.defer(ephemeral=True)
        report = await order_product_from_command(
            str(interaction.user.id), shop, product
        )
        if report is None:
            report = "Unknown error. Contact system admin."
        await interaction.followup.send(report, ephemeral=True)

    @app_commands.command(description="Order a product from a shop as someone else")
    async def order_other(
        self, interaction: Interaction, buyer: str, product: str, shop: str
    ):
        pass
