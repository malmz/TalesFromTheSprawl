import discord
from discord import ui


class TestView(ui.View):
    @ui.button(label="0", style=discord.ButtonStyle.red)
    async def count(self, interaction: discord.Interaction, button: ui.Button):
        number = int(button.label) if button.label else 0
        if number + 1 >= 5:
            button.style = discord.ButtonStyle.green
            button.disabled = True
        button.label = str(number + 1)
        await interaction.response.edit_message(view=self)
