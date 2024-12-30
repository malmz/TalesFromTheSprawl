import logging

import discord
from discord import Interaction, Member, app_commands, utils
from discord.app_commands.errors import MissingRole, NoPrivateMessage
from discord.ext import commands

from talesbot import actors, gm, groups, handles, players

logger = logging.getLogger(__name__)


@app_commands.guild_only()
class AdminCog(commands.GroupCog, group_name="admin"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def interaction_check(self, interaction: Interaction) -> bool:
        """Check for gm role"""
        if isinstance(interaction.user, discord.User):
            raise NoPrivateMessage()

        role = utils.get(interaction.user.roles, name=gm.role_name)

        if role is None:
            raise MissingRole(gm.role_name)
        return True

    player = app_commands.Group(name="player", description="Manage players")

    @player.command(
        name="init_all",
        description="Initialise all current members of the server as players",
    )
    async def init_all_players(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        await players.initialise_all_users()
        await interaction.followup.send("Done.", ephemeral=True)

    @player.command(name="join", description="Initialise a user as a player")
    async def fake_join(self, interaction: Interaction, member: Member, handle: str):
        await interaction.response.defer(ephemeral=True)
        async with handles.semaphore():
            report = await players.create_player(member, handle)
            if report is None:
                report = "Done."
        await interaction.followup.send(report, ephemeral=True)

    @player.command(name="clear_all", description="De-initialise all players")
    async def clear_all_players(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        await players.init(clear_all=True)
        try:
            await interaction.followup.send("Done.", ephemeral=True)
        except discord.errors.NotFound:
            logger.warning(
                "Cleared all players. Could not send report because channel is missing "
                "- the command was probably given in a player-only command "
                "line that was deleted."
            )

    actor = app_commands.Group(name="actor", description="Manage actors")

    @actor.command(
        name="clear_all",
        description="De-initialise all actors (players and shops)",
    )
    async def clear_all_actors(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        await actors.init(clear_all=True)
        try:
            await interaction.followup.send("Done.", ephemeral=True)
        except discord.errors.NotFound:
            logger.warning(
                "Cleared all actors. Could not send report because channel is missing"
                " - the command was probably given in a player-only command "
                "line that was deleted."
            )

    @actor.command(
        name="clear",
        description="De-initialise an actor (player or shop)",
    )
    async def clear_actor(self, interaction: Interaction, actor_id: str):
        await interaction.response.defer(ephemeral=True)
        report = await actors.clear_actor(actor_id)
        try:
            await interaction.followup.send(report, ephemeral=True)
        except discord.errors.NotFound:
            logger.warning(
                f"Cleared actor {actor_id}. Could not send report because channel"
                " is missing - the command was probably given in a player-only "
                "command line that was deleted."
            )

    @clear_actor.autocomplete("actor_id")
    async def clear_actor_autocomplete(
        self, interaction: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=id, value=id)
            for id in actors.get_all_actor_ids()
            if current.lower() in id.lower()
        ]

    @app_commands.command(
        description="Send a ping to a player's cmd_line channel",
    )
    async def ping(self, interaction: Interaction, player_id: str):
        await interaction.response.defer(ephemeral=True)
        channel = players.get_cmd_line_channel(player_id)
        if channel is not None:
            await channel.send(f"Testing ping for {player_id}")
            await interaction.followup.send("OK", ephemeral=True)
        else:
            await interaction.followup.send(
                f"Error: could not find the command line channel for {player_id}",
                ephemeral=True,
            )

    @ping.autocomplete("player_id")
    async def ping_autocomplete(
        self, interaction: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=id, value=id)
            for id in players.get_all_players()
            if current.lower() in id.lower()
        ]

    group = app_commands.Group(name="group", description="Manage groups")

    @group.command(name="add", description="Add a member to a group")
    async def add_group(self, interaction: Interaction, handle_id: str, group_id: str):
        await interaction.response.defer(ephemeral=True)
        report = await groups.add_member_from_handle(
            interaction.guild, group_id, handle_id
        )
        if report is not None:
            await interaction.followup.send(report, ephemeral=True)
        else:
            await interaction.followup.send(
                "Failed to add member from handle", ephemeral=True
            )

    @add_group.autocomplete("handle_id")
    async def add_handle_id_autocomplete(
        self, interaction: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=handle.handle_id, value=handle.handle_id)
            for handle in handles.get_all_handles()
            if current.lower() in handle.handle_id.lower()
        ]

    @add_group.autocomplete("group_id")
    async def add_group_id_autocomplete(
        self, interaction: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=id, value=id)
            for id in groups.get_all_group_ids()
            if current.lower() in id.lower()
        ]

    @group.command(
        name="create",
        description="Create a group with yourself as initial member",
    )
    async def create_group(self, interaction: Interaction, group_name: str):
        await interaction.response.defer(ephemeral=True)
        report = await groups.create_group_from_command(interaction.user.id, group_name)
        if report is not None:
            await interaction.followup.send(report, ephemeral=True)

    @group.command(name="clear_all", description="Delete all groups")
    async def clear_all_groups(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        await groups.init(clear_all=True)
        await interaction.followup.send("Done.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
