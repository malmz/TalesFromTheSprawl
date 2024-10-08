import asyncio
import logging
from typing import List, cast

import discord
from configobj import ConfigObj

from talesbot import gm

from . import actors, channels, common, player_setup, server, shops
from .common import (
    admin_role_name,
    highest_ever_index,
    player_personal_role_start,
)
from .config import config_dir
from .custom_types import Handle, PlayerData
from .groups import Group

players_conf_dir = "players"
user_id_mappings_index = "___user_id_to_player_id"
guild_to_user_count_index = "__guild_to_user_count"
logger = logging.getLogger(__name__)


def get_players_confobj():
    players = ConfigObj(str(config_dir / players_conf_dir / "__players.conf"))
    if user_id_mappings_index not in players:
        players[user_id_mappings_index] = {}
        players.write()
    if guild_to_user_count_index not in players:
        players[guild_to_user_count_index] = {}
        players.write()
    return players


# TODO: loop through all users, find their player_ids and re-map personal channels if not available
async def init(clear_all=False):
    players = get_players_confobj()
    if user_id_mappings_index not in players or clear_all:
        players[user_id_mappings_index] = {}
    if guild_to_user_count_index not in players or clear_all:
        players[guild_to_user_count_index] = {}
    if highest_ever_index not in players[user_id_mappings_index] or clear_all:
        players[user_id_mappings_index][highest_ever_index] = str(
            player_personal_role_start
        )
    if clear_all:
        for player_id in get_all_players():
            await _clear_player(player_id)
            del players[player_id]
    await _delete_all_player_roles(spare_used=not clear_all)

    players.write()


async def _delete_all_player_roles(spare_used: bool):
    task_list = (
        asyncio.create_task(delete_if_player_role(r, spare_used))
        for guild in server.get_guilds()
        for r in guild.roles
    )
    await asyncio.gather(*task_list)


async def delete_if_player_role(role, spare_used: bool):
    if common.is_player_role(role.name):
        if not spare_used or len(role.members) == 0:
            await role.delete()


async def _clear_player(player_id: str):
    logger.debug(f"Clearing player {player_id}")
    await actors.clear_actor(player_id)
    await channels.delete_all_personal_channels(player_id)
    player: PlayerData = read_player_data(player_id)
    for shop_id in player.shops:
        await shops.remove_employee_player(shop_id, player_id)
    logger.debug(f"Removing {player_id} from all groups: {player.groups}")
    for group_id in player.groups:
        group = Group.read(group_id)
        if group is not None:
            await group.remove_member(player_id)


async def initialise_all_users():
    task_list = (
        asyncio.create_task(create_player(m))
        for guild in server.get_guilds()
        for m in guild.members
        if not m.bot
    )
    await asyncio.gather(*task_list)


def get_all_players():
    players = get_players_confobj()
    for player in players:
        if player not in [
            highest_ever_index,
            user_id_mappings_index,
            guild_to_user_count_index,
        ]:
            yield cast(str, player)


def player_exists(player_id: str):
    return player_id in get_all_players()


def is_player(player_id: str):
    return player_id in get_all_players()


def store_player_data(player_data: PlayerData):
    players = get_players_confobj()
    players[player_data.player_id] = player_data.to_string()
    players.write()


def read_player_data(player_id: str):
    players = get_players_confobj()
    if player_id in players:
        return PlayerData.from_string(players[player_id])


def get_player_id(user_id: str, expect_to_find=True) -> str | None:
    players = get_players_confobj()
    if user_id not in players[user_id_mappings_index]:
        if expect_to_find:
            logger.warning(f"User {user_id} has not been initialized as a player")
            raise RuntimeError(
                "User has not been initialized as a player. Did you run /join?"
            )
        return None
    return players[user_id_mappings_index][user_id]  # type: ignore


def get_player_category_index(player_id: str):
    player = read_player_data(player_id)
    if player is None:
        logger.debug(f"Using default category index 0 for non-player {player_id}")
        return 0
    return player.category_index


def get_next_player_index():
    players = get_players_confobj()
    prev_highest = int(players[user_id_mappings_index][highest_ever_index])
    player_index = str(prev_highest + 1)
    players[user_id_mappings_index][highest_ever_index] = player_index
    players.write()
    return player_index


async def create_player(member: discord.Member, handle_id: str):
    if not player_setup.can_setup_new_player_with_handle(handle_id):
        return f'Failed: invalid starting handle "{handle_id}" (or handle is already taken).'
    user_id = str(member.id)
    existing_player_id = get_player_id(user_id, expect_to_find=False)
    if existing_player_id is not None:
        return f"Error: Could not create player for member {user_id}, since they already have player_id {existing_player_id}."

    new_player_index = get_next_player_index()
    new_player_id = "u" + new_player_index

    # Set user id
    players = get_players_confobj()
    players[user_id_mappings_index][user_id] = new_player_id
    players.write()

    # Figure out category id
    guild_id = str(member.guild.id)
    if guild_id not in players[guild_to_user_count_index]:
        players[guild_to_user_count_index][guild_id] = str(1)
    players_in_guild = int(players[guild_to_user_count_index][guild_id])
    category_index = 1 + (
        (players_in_guild - 1) // 3
    )  # first player category is 1. 3 players/category
    players[guild_to_user_count_index][guild_id] = str(players_in_guild + 1)
    players.write()

    # Pre-store player data to make category available
    player_data = PlayerData(new_player_id, category_index, 0)
    store_player_data(player_data)

    # A player is a type of actor, so we start by creating an actor for this member/user
    actor: actors.Actor = await actors.create_new_actor(
        member.guild, actor_index=new_player_index, actor_id=new_player_id
    )
    role = actors.get_actor_role(actor.actor_id)

    # Create personal command line channels for player
    cmd_line_channel = await channels.create_personal_channel(
        member.guild,
        role,
        channels.get_cmd_line_name(new_player_id),
        new_player_id,
        category_index,
    )

    # Edit user (change nick and add role):
    new_roles = member.roles
    new_roles.append(role)
    all_players_role = server.get_all_players_role(member.guild)
    if all_players_role not in new_roles:
        new_roles.append(all_players_role)
    new_player_role = server.get_new_player_role(member.guild)
    new_roles = [r for r in new_roles if r.name != new_player_role.name]
    await member.edit(roles=new_roles)
    try:
        await member.edit(nick=new_player_id)
    except discord.Forbidden:
        logger.error(
            f"Probably tried to edit server owner, which doesn't work. Please make sure user {member.name} has nickname {new_player_id}."
        )

    player_data = PlayerData(new_player_id, category_index, cmd_line_channel.id)
    store_player_data(player_data)

    success = await player_setup.setup_handles_and_welcome_new_player(
        player_data, handle_id
    )
    if not success:
        return f"Error! Created player {player_data.player_id} but could not set up handle {handle_id}!"

    return None


def get_cmd_line_channels_for_handles(handles: List[str]):
    actor_set = set()  # Use a set to weed out duplicates
    for handle_id in handles:
        actor = actors.get_actor_for_handle(handle_id)
        if actor is not None:
            actor_set.add(actor)
    channel_list = []
    for actor in actor_set:
        channel = get_cmd_line_channel(actor.actor_id)
        if channel is not None:
            channel_list.append(channel)
    return channel_list


def get_cmd_line_channel_for_handle(handle: Handle):
    actor: actors.Actor = actors.get_actor_for_handle(handle)
    if actor is not None:
        return get_cmd_line_channel(actor.actor_id)


def get_cmd_line_channel(player_id: str):
    data: PlayerData = read_player_data(player_id)
    if data is not None:
        guild = actors.get_guild_for_actor(player_id)
        return channels.get_discord_channel(data.cmd_line_channel_id, guild.id)


# Shops


def add_shop(player_id: str, shop_id: str):
    player: PlayerData = read_player_data(player_id)
    if shop_id not in player.shops:
        player.shops.append(shop_id)
        store_player_data(player)


def remove_shop(player_id: str, shop_id: str):
    player: PlayerData = read_player_data(player_id)
    if player is not None and shop_id in player.shops:
        player.shops = [s for s in player.shops if s != shop_id]
        store_player_data(player)


def get_shops(player_id: str):
    return read_player_data(player_id).shops


# Groups


def add_group(player_id: str, group_id: str):
    player: PlayerData = read_player_data(player_id)
    logger.debug(
        f"Trying to add {player_id} to {group_id}; existing groups are {player.groups}"
    )
    if player is not None and group_id not in player.groups:
        player.groups.append(group_id)
        store_player_data(player)


def remove_group(player_id: str, group_id: str):
    player: PlayerData = read_player_data(player_id)
    if player is not None and group_id in player.groups:
        player.groups = [g for g in player.groups if g != group_id]
        store_player_data(player)


async def is_gm(player_id: str):
    if player_exists(player_id):
        member = await server.get_member_from_nick(player_id)
        return server.check_member_has_role(member, [gm.role_name])


async def is_admin(player_id: str):
    if player_exists(player_id):
        member = await server.get_member_from_nick(player_id)
        return server.check_member_has_role(member, [admin_role_name])


async def is_gm_or_admin(player_id: str):
    if player_exists(player_id):
        member = await server.get_member_from_nick(player_id)
        logger.debug(f"Checking if {player_id} is gm or admin")
        return server.check_member_has_role(member, [gm.role_name, admin_role_name])
