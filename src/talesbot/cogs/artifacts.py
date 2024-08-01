"""
This module handles the creation and execution of in-game artifacts, which are items that can be accessed through
logging in with codes.
"""

import json
import os

from discord import Interaction, app_commands
from discord.ext import commands

from .. import common, handles, players, server

# TODO: reinitialise?


class ArtifactsCog(commands.Cog, name="network"):
    """Commands for connecting to devices and accessing files."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        description="Connect to device or remote server. Aliases: /login, /access",
    )
    async def connect(self, interaction: Interaction, code: str, password: str = None):
        await self.do_connect(interaction, code, password)

    @app_commands.command(
        description="Connect to device or remote server. Same as /connect.",
    )
    async def login(self, interaction: Interaction, code: str, password: str = None):
        await self.do_connect(interaction, code, password)

    @app_commands.command(
        description="Connect to device or remote server. Same as /connect.",
    )
    async def access(self, interaction: Interaction, code: str, password: str = None):
        await self.do_connect(interaction, code, password)

    async def do_connect(
        self, interaction: Interaction, code: str, password: str = None
    ):
        await interaction.response.defer(ephemeral=True)
        (report, announcement) = access_artifact(code, password)
        await self.log_connect_attempt(
            str(interaction.user.id), code, password, announcement
        )
        if report is not None:
            await interaction.followup.send(report, ephemeral=True)
        else:
            await interaction.followup.send("Unable to connect.", ephemeral=True)

    async def log_connect_attempt(
        self, user_id: str, code: str, password: str, announcement: str = None
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


async def setup(bot):
    await bot.add_cog(ArtifactsCog(bot))


artifacts_conf_dir = "artifacts"
artifacts_conf_file = f"{artifacts_conf_dir}/artifacts.json"


class Artifact:
    def __init__(self, name, data):
        self.name = name
        self.codes = data.get("codes", {})
        self.announcement_message = data.get("announcement_message", None)

    def get_data(self, pw):
        if pw is None:
            pw = "default"

        if pw in self.codes:
            path = f"{artifacts_conf_dir}/{self.codes[pw]}"
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            return "Unable to find artifact data. Contact system admin"
        return f'Error trying to access {self.name}: incorrect credentials "{pw}".'

    def get_announcement(self):
        return self.announcement_message


def find_artifact(name):
    with open(artifacts_conf_file) as f:
        data = json.load(f)
    if name in data:
        return Artifact(name, data[name])


def create_artifact(name: str, content: str = None):
    if name is None:
        return "Error: you must give a name for the artifact."

    # Find free filename
    filename = f"{name}.data"
    i = 2
    while os.path.exists(f"{artifacts_conf_dir}/{filename}"):
        filename = f"{name}_{i}.data"
        i += 1

    # Write data file
    out_path = f"{artifacts_conf_dir}/{filename}"
    with open(out_path, "w") as out_file:
        out_file.write(content)

    # Add data to config file
    with open(artifacts_conf_file, "r") as f:
        data = json.load(f)
    data[name] = {"codes": {"default": filename}}

    # Write to config file
    with open(artifacts_conf_file, "w") as art_out:
        json.dump(data, art_out, indent=4)

    return f"Created artifact {name}."


def access_artifact(name: str, code: str):
    if name is None:
        return (
            f"Error: you must give the name of the entity you want to access.",
            None,
        )
    artifact = find_artifact(name)
    if artifact is None:
        return (f'Error: entity "{name}" not found. Check the spelling.', None)
    return (artifact.get_data(code), artifact.get_announcement())
