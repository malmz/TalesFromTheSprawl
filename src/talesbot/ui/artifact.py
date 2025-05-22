import discord
from discord import Interaction, ui

from ..database.models import Artifact


class NextButton(ui.Button["ArtifactView"]):
    def __init__(self):
        super().__init__(label="Next", disabled=True)

    async def callback(self, interaction: Interaction):
        assert self.view is not None
        view = self.view
        view.page = min(view.page + 1, view.last_page)
        view.update_button_state()

        content_page = view.artifact.content[view.page]
        if content_page is not None:
            await interaction.response.edit_message(
                content=content_page.content, view=view
            )
        else:
            await interaction.response.edit_message(
                content="[no more pages]", view=None
            )


class PrevButton(ui.Button["ArtifactView"]):
    def __init__(self):
        super().__init__(label="Prev", disabled=True)

    async def callback(self, interaction: Interaction):
        assert self.view is not None
        view = self.view
        view.page = max(view.page - 1, 0)
        view.update_button_state()

        content_page = view.artifact.content[view.page]
        if content_page is not None:
            await interaction.response.edit_message(
                content=content_page.content, view=view
            )
        else:
            await interaction.response.edit_message(
                content="[no more pages]", view=None
            )


class ArtifactView(
    ui.View,
):
    def __init__(self, artifact: Artifact, page: int = 0) -> None:
        super().__init__(timeout=100)
        self.artifact = artifact
        self.page: int = page
        self.last_page = len(self.artifact.content) - 1

        self.next = NextButton()
        self.prev = PrevButton()

        if len(self.artifact.content) > 1:
            self.add_item(self.prev)
            self.add_item(self.next)

        self.update_button_state()

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
