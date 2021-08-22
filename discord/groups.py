# module groups.py

### This module collects storage and utilities for groups, which are essentially access roles that
# more than one player can share.
# TODO: a shop could be implemented with a group as a base, to represent the employees and access part of it
# Possible refactoring: split "actor" into "access role" (which groups, players and shops all share)
# and "finance and chat capabilities", which only players and shops have
# (this would avoid the double-implementation of access roles that currently exists between groups and actors)

import discord
import asyncio
import simplejson

from configobj import ConfigObj
from typing import List, Tuple
from copy import deepcopy
from enum import Enum

# Custom imports
import common
import channels
import actors
import server
import players
import handles

from common import emoji_alert, emoji_accept, group_role_start, highest_ever_index
from custom_types import ActionResult, Group, Handle, HandleTypes


groups_conf_dir = 'groups'
groups = ConfigObj(f'{groups_conf_dir}/groups.conf')
groups_input = ConfigObj('groups_input.conf')

# Init and utils

async def init(guild, clear_all=False):
	if clear_all:
		for group_id in get_all_group_ids():
			await clear_group(guild, group_id)
		await channels.delete_all_group_channels()
	else:
		for group in get_all_groups():
			# TODO: re-map stuff?
			pass
	if highest_ever_index not in groups or clear_all:
		groups[highest_ever_index] = str(group_role_start)		
		groups.write()	
	await delete_all_group_roles(guild, spare_used=(not clear_all))

async def clear_group(guild, group_id : str):
	if group_exists(group_id):
		group = read_group(group_id)
		# TOOD: update all actors that think they belong to this group
		del groups[group_id]
		groups.write()
		await delete_all_group_roles(guild, spare_used=True)
		return 'Done'
	else:
		return f'Could not find group {group_id}'

async def delete_all_group_roles(guild, spare_used : bool):
	task_list = (asyncio.create_task(delete_if_group_role(r, spare_used)) for r in guild.roles)
	await asyncio.gather(*task_list)

async def delete_if_group_role(role, spare_used : bool):
	if await is_group_role(role.name):
		if not spare_used or len(role.members) == 0:
			print(f'Deleting unused role with name {role.name}')
			await role.delete()

async def is_group_role(name :str):
	return common.is_group_role(name)

def get_group_role(guild, group_id : str):
	group = read_group(group_id)
	if group is not None:
		return discord.utils.find(lambda role: role.name == group.group_index, guild.roles)


def get_all_groups():
	for group_id in get_all_group_ids():
		yield read_group(group_id)

def get_all_group_ids():
	for group_id in groups:
		if group_id != highest_ever_index:
			yield group_id

def group_exists(group_id : str):
	if group_id is not None:
		return group_id.lower() in groups

def store_group(group : Group):
	groups[group.group_id] = group.to_string()
	groups.write()

def read_group(group_name : str):
	if group_name is not None:
		group_id = group_name.lower()
		if group_id in get_all_group_ids():
			return Group.from_string(groups[group_id])

def get_next_group_index():
	prev_highest = int(groups[highest_ever_index])
	group_index = str(prev_highest + 1)
	groups[highest_ever_index] = group_index
	groups.write()
	return group_index

def get_main_channel(group_id : str):
	group : Group = read_group(group_id)
	if group is not None:
		return channels.get_discord_channel(group.main_channel_id)



# Create group

async def create_group_from_command(ctx, group_id : str):
	if group_id is None:
		return f'Error: must give a group name.'

	player_id = players.get_player_id(str(ctx.message.author.id))
	if player_id is not None:
		members = [player_id]
		members_report = f' The first member is {player_id}'
	else:
		members = []
		members_report = ''
	group_index = get_next_group_index()
	group = await create_new_group(ctx.guild, group_index, group_id, initial_members=members)
	return f'Created group \"{group.group_id}\".' + members_report

async def create_new_group(guild, group_index : str, group_name : str, initial_members : List[str] = []):
	# Create role for this group:
	role = await guild.create_role(name=group_index)
	group_id = group_name.lower()
	channel = await channels.create_group_channel(guild, role, group_id)

	for player_id in initial_members:
		member = await server.get_member_from_nick(player_id)
		if member is not None:
			await server.give_member_role(member, role)

	group = Group(
		group_index=group_index,
		group_id=group_id,
		main_channel_id=str(channel.id),
		members=initial_members)
	store_group(group)
	return group


# Edit groups

async def add_member(guild, handle_id : str, group_id : str):
	if handle_id is None:
		return f'Error: you must give a handle ID and group name. Use \".add_member <handle> <group>\"'
	handle : Handle = handles.get_handle(handle_id)
	if handle.handle_type == HandleTypes.Unused:
		return f'Error: handle {handle_id} does not exist.'
	member = await server.get_member_from_nick(handle.actor_id)
	if member is None:
		return f'Error: actor {handle.actor_id} is not a player, or does not follow the server nick scheme.'
	if group_id is None:
		return f'Error: you must give a group name. Use \".add_member {handle_id} <group>\"'
	group : Group = read_group(group_id)
	if group is None:
		return f'Error: could not find group {group_id}.'

	if handle.actor_id in group.members:
		return f'Error: player {handle.actor_id} (owner of handle {handle.handle_id}) is already a member of {group.group_id}.'
	group.members.append(handle.actor_id)
	store_group(group)

	role = get_group_role(guild, group.group_id)
	await server.give_member_role(member, role)
	return f'Added {handle.handle_id} to group {group.group_id}.'
		



# Use groups

async def give_group_access(guild, channel, group_id : str):
	role = get_group_role(guild, group_id)
	await server.give_role_access(channel, role)


