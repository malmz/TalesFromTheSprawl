"""
Module the holds the admin commands
"""

import discord
from discord import Interaction, app_commands
from discord.ext import commands

from .. import actors, common, groups, handles, players, server

# TODO: change these to be admin-only (currently they are actually GM-only)
# TODO: grab the name of the admin role from env file


@app_commands.default_permissions(administrator=True)
class AdminCog(commands.GroupCog, group_name="admin"):
    """Admin-only commands, hidden by default. To view documentation, use \"help <command>\". The commands are:
    init_all_players, fake_join, fake_join_name, fake_join_nick, clear_all_players, clear_all_actors, clear_actor, ping
    """

    def __init__(self, bot):
        self.bot = bot

    # This command is not safe right now.
    @app_commands.command(
        description="Initialise all current members of the server as players",
    )
    async def init_all_players(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        await players.initialise_all_users()
        await interaction.followup.send("Done.", ephemeral=True)

    @app_commands.command(description="Initialise a user as a player")
    async def fake_join(self, interaction: Interaction, user_id: int, handle: str):
        await interaction.response.defer(ephemeral=True)
        member_to_fake_join = await interaction.guild.fetch_member(user_id)
        if member_to_fake_join is None:
            await interaction.followup.send(
                f"Failed: member with user_id {user_id} not found.", ephemeral=True
            )
        elif handle is None:
            await interaction.followup.send(
                "Failed: you must give the player's main handle.", ephemeral=True
            )
        else:
            async with handles.semaphore():
                report = await players.create_player(member_to_fake_join, handle)
                if report is None:
                    report = "Done."
            await interaction.followup.send(report, ephemeral=True)

    @app_commands.command(
        description="Initialise a user as a player (based on discord name)",
    )
    async def fake_join_name(self, interaction: Interaction, name: str, handle: str):
        await interaction.response.defer(ephemeral=True)
        member_to_fake_join = None
        async for member in interaction.guild.fetch_members(limit=100):
            if member.name == name:
                member_to_fake_join = member
                break
        if member_to_fake_join is None:
            await interaction.followup.send(
                f"Failed: member with name {name} not found.", ephemeral=True
            )
        elif handle is None:
            await interaction.followup.send(
                "Failed: you must give the player's main handle.", ephemeral=True
            )
        else:
            async with handles.semaphore():
                report = await players.create_player(member_to_fake_join, handle)
                if report is None:
                    report = "Done."
            await interaction.followup.send(report, ephemeral=True)

    @app_commands.command(
        description="Initialise a user as a player (based on server nick)",
    )
    async def fake_join_nick(self, interaction: Interaction, nick: str, handle: str):
        await interaction.response.defer(ephemeral=True)
        member_to_fake_join = await server.get_member_from_nick(nick)
        if member_to_fake_join is None:
            await interaction.followup.send(
                f"Failed: member with nick {nick} not found.", ephemeral=True
            )
        elif handle is None:
            await interaction.followup.send(
                "Failed: you must give the player's main handle.", ephemeral=True
            )
        else:
            async with handles.semaphore():
                report = await players.create_player(member_to_fake_join, handle)
                if report is None:
                    report = "Done."
            await interaction.followup.send(report, ephemeral=True)

    # This command ONLY works in the landing page channel.
    # Note: no other commands work in the landing page channel!
    # TODO: semaphore for joining
    @app_commands.command(
        description="Claim a handle and join the game. Only for players who have not yet joined",
    )
    @app_commands.checks.has_role(common.new_player_role_name)
    async def join(self, interaction: Interaction, handle: str):
        await interaction.response.defer(ephemeral=True)
        member = await interaction.guild.fetch_member(interaction.user.id)
        if member is None:
            await interaction.followup.send("Failed: member not found.", ephemeral=True)
        elif handle is None or handle == "handle" or handle == "<handle>":
            await interaction.followup.send(
                'You must say which handle is yours! Example: "/join shadow_weaver"',
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

    @app_commands.command(description="De-initialise all players.")
    async def clear_all_players(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        await players.init(clear_all=True)
        try:
            await interaction.followup.send("Done.", ephemeral=True)
        except discord.errors.NotFound:
            print(
                "Cleared all players. Could not send report because channel is missing - "
                + "the command was probably given in a player-only command line that was deleted."
            )

    @app_commands.command(
        description="Admin-only: de-initialise all actors (players and shops).",
    )
    async def clear_all_actors(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        await actors.init(clear_all=True)
        try:
            await interaction.followup.send("Done.", ephemeral=True)
        except discord.errors.NotFound:
            print(
                "Cleared all actors. Could not send report because channel is missing - "
                + "the command was probably given in a player-only command line that was deleted."
            )

    @app_commands.command(
        description="Admin-only: de-initialise an actor (player or shop).",
    )
    async def clear_actor(self, interaction: Interaction, actor_id: str):
        await interaction.response.defer(ephemeral=True)
        report = await actors.clear_actor(actor_id)
        try:
            await interaction.followup.send(report, ephemeral=True)
        except discord.errors.NotFound:
            print(
                f"Cleared actor {actor_id}. Could not send report because channel is missing - "
                + "the command was probably given in a player-only command line that was deleted."
            )

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

    @app_commands.command(description="Add a member to a group")
    async def add_member(self, interaction: Interaction, handle_id: str, group_id: str):
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

    @app_commands.command(
        description="Create a group with yourself as initial member",
    )
    async def create_group(self, interaction: Interaction, group_name: str):
        await interaction.response.defer(ephemeral=True)
        report = await groups.create_group_from_command(interaction.user.id, group_name)
        if report is not None:
            await interaction.followup.send(report, ephemeral=True)

    @app_commands.command(description="Delete all groups")
    async def clear_all_groups(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        await groups.init(clear_all=True)
        await interaction.followup.send("Done.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
