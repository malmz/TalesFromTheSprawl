import discord
from discord import ui

from ..database.models import Artifact


class ArtifactView(
    ui.View,
):
    def __init__(self, artifact: Artifact, page: int = 0) -> None:
        self.artifact = artifact
        self.page: int = page
        self.last_page = len(self.artifact.content) - 1

        super().__init__(timeout=100)
        self.update_button_state()

    @ui.button(label="Prev", disabled=True)
    async def prev(self, interaction: discord.Interaction, button: ui.Button):
        self.page = max(self.page - 1, 0)
        self.update_button_state()

        content_page = self.artifact.content[self.page]
        if content_page is not None:
            await interaction.response.edit_message(
                content=content_page.content, view=self
            )
        else:
            await interaction.response.edit_message(
                content="[no more pages]", view=None
            )

    @ui.button(label="Next", disabled=True)
    async def next(self, interaction: discord.Interaction, button: ui.Button):
        self.page = min(self.page + 1, self.last_page)
        self.update_button_state()

        content_page = self.artifact.content[self.page]
        if content_page is not None:
            await interaction.response.edit_message(
                content=content_page.content, view=self
            )
        else:
            await interaction.response.edit_message(
                content="[no more pages]", view=None
            )

    def update_button_state(self):
        self.next.disabled = self.page == self.last_page
        self.next.style = (
            discord.ButtonStyle.gray
            if self.page == self.last_page
            else discord.ButtonStyle.blurple
        )
        self.prev.disabled = self.page == 0
        self.prev.style = (
            discord.ButtonStyle.gray if self.page == 0 else discord.ButtonStyle.blurple
        )
