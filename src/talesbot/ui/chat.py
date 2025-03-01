import re
from enum import StrEnum

from discord import ButtonStyle, Interaction, ui


class ChatAction(StrEnum):
    OPEN = "open"
    CLOSE = "close"


class ChatButton(
    ui.DynamicItem[ui.Button],
    template=r"tfts:chat:(?P<name>[\w]+):(?P<action>open|close)",
):
    name: str
    action: ChatAction

    def __init__(self, name: str, action: ChatAction):
        self.name = name
        self.action = action
        super().__init__(
            ui.Button(
                label=action, style=self.style, custom_id=f"tfts:chat:{name}:{action}"
            )
        )

    @property
    def style(self):
        match self.action:
            case ChatAction.OPEN:
                return ButtonStyle.green
            case ChatAction.CLOSE:
                return ButtonStyle.red

    @classmethod
    async def from_custom_id(
        cls, interaction: Interaction, item: ui.Item, match: re.Match[str], /
    ):
        name = str(match["name"])
        action = ChatAction(match["action"])
        return cls(name, action)

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.send_message(
            "This is your very own button!", ephemeral=True
        )
