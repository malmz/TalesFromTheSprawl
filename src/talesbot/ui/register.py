import logging

import discord
from discord import ui

logger = logging.getLogger(__name__)


class HandleModal(ui.Modal, title="Register as player"):
    handle = ui.TextInput(
        label="Enter main handle provided in player document",
        placeholder="Your main handle...",
    )

    async def on_submit(self, interaction: discord.Interaction):
        from talesbot import handles, players  # Avoid dependency cycle

        await interaction.response.defer(ephemeral=True)
        handle = self.handle.value
        member = await interaction.guild.fetch_member(interaction.user.id)
        if member is None:
            await interaction.followup.send("Failed: member not found.", ephemeral=True)
        elif handle is None or handle == "handle" or handle == "<handle>":
            await interaction.followup.send(
                'You must say which handle is yours! Example: "shadow_weaver"',
                ephemeral=True,
            )
        else:
            async with handles.semaphore():
                # TODO give player some sort of warning about using lower-case only
                handle_id = handle.lower()
                report = await players.create_player(member, handle_id)
            if report is not None:
                await interaction.followup.send(
                    f'Failed: invalid starting handle "{handle_id}" (or handle is already taken).',
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "Success! Now have a look at all your new channels 🥳",
                    ephemeral=True,
                )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message(
            "Oops! Something went wrong.", ephemeral=True
        )
        logger.error("failed to register player", exc_info=error)


class RegisterView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Register as player",
        style=discord.ButtonStyle.primary,
        custom_id="talesbot:register",
    )
    async def register(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(HandleModal())
