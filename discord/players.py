import channels
import handles
import reactions
import common
import server
import actors
import shops
import groups

from common import coin, highest_ever_index, player_personal_role_start, admin_role_name, gm_role_name

from custom_types import PlayerData, Handle

import discord
import asyncio
from configobj import ConfigObj
from typing import List


players_conf_dir = 'players'
user_id_mappings_index = '___user_id_to_player_id'

def get_players_confobj():
	players = ConfigObj(players_conf_dir + '/__players.conf')
	if not user_id_mappings_index in players:
		players[user_id_mappings_index] = {}
		players.write()
	return players


# TODO: loop through all users, find their player_ids and re-map personal channels if not available
async def init(guild, clear_all=False):
	players = get_players_confobj()
	if not user_id_mappings_index in players or clear_all:
		players[user_id_mappings_index] = {}
	if not highest_ever_index in players[user_id_mappings_index] or clear_all:
		players[user_id_mappings_index][highest_ever_index] = str(player_personal_role_start)
	if clear_all:
		for player_id in get_all_players():
			await clear_player(guild, player_id)
			del players[player_id]
	await delete_all_player_roles(guild, spare_used=not clear_all)

	players.write()


async def delete_all_player_roles(guild, spare_used : bool):
	task_list = (asyncio.create_task(delete_if_player_role(r, spare_used)) for r in guild.roles)
	await asyncio.gather(*task_list)

async def delete_if_player_role(role, spare_used : bool):
	if common.is_player_role(role.name):
		if not spare_used or len(role.members) == 0:
			await role.delete()

async def clear_player(guild, player_id : str):
	await actors.clear_actor(guild, player_id)
	await channels.delete_all_personal_channels(player_id)
	player : PlayerData = read_player_data(player_id)
	for shop_id in player.shops:
		await shops.remove_employee_player(shop_id, player_id)
	print(f'Removing {player_id} from all groups: {player.groups}')
	for group_id in player.groups:
		await groups.remove_member(group_id, player_id)

async def initialise_all_users():
	guild = server.get_guild()
	task_list = (asyncio.create_task(create_player(m)) for m in guild.members if not m.bot)
	await asyncio.gather(*task_list)

def get_all_players():
	players = get_players_confobj()
	for player in players:
		if not player in [highest_ever_index, user_id_mappings_index]:
			yield player

def player_exists(player_id : str):
	return player_id in get_all_players()

def is_player(actor_id : str):
	return player_id in get_all_players()

def store_player_data(player_data : PlayerData):
	players = get_players_confobj()
	players[player_data.player_id] = player_data.to_string()
	players.write()

def read_player_data(player_id : str):
	players = get_players_confobj()
	if player_id in players:
		return PlayerData.from_string(players[player_id])


def get_player_id(user_id : str, expect_to_find=True):
	players = get_players_confobj()
	if not user_id in players[user_id_mappings_index]:
		if expect_to_find:
			raise RuntimeError(f'User {user_id} has not been initialized as a player. Fix that first.')
		else:
			return None
	return players[user_id_mappings_index][user_id];


def get_next_player_actor_index():
	players = get_players_confobj()
	prev_highest = int(players[user_id_mappings_index][highest_ever_index])
	actor_index = str(prev_highest + 1)
	players[user_id_mappings_index][highest_ever_index] = actor_index
	players.write()
	return actor_index

async def create_player(member):
	user_id = str(member.id)
	existing_player_id = get_player_id(user_id, expect_to_find=False)
	if existing_player_id is not None:
		return f'Error: Could not create player for member {user_id}, since they already have player_id {existing_player_id}.'

	new_player_index = get_next_player_actor_index()
	new_player_id = 'u' + new_player_index

	# A player is a type of actor, so we start by creating an actor for this member/user
	actor : actors.Actor = await actors.create_new_actor(member.guild, actor_index=new_player_index, actor_id=new_player_id)
	role = actors.get_actor_role(member.guild, actor.actor_id)
	
	players = get_players_confobj()
	players[user_id_mappings_index][user_id] = new_player_id
	players.write()

	# Create personal command line channels for player
	cmd_line_channel = await channels.create_personal_channel(
		member.guild,
		role,
		channels.get_cmd_line_name(new_player_id)
	)

	# Send welcome messages before adding the role -> avoid spamming notifications
	await send_startup_message_cmd_line(new_player_id, cmd_line_channel)

	# Edit user (change nick and add role):
	new_roles = member.roles
	new_roles.append(role)
	all_players_role = server.get_all_players_role()
	if all_players_role not in new_roles:
		new_roles.append(server.get_all_players_role())
	await member.edit(roles=new_roles)
	try:
		await member.edit(nick = new_player_id)
	except discord.Forbidden:
		print(f'Probably tried to edit server owner, which doesn\'t work. Please make sure user {member.name} has nickname {new_player_id}.')

	player_data = PlayerData(new_player_id, cmd_line_channel.id)
	store_player_data(player_data)

async def send_startup_message_cmd_line(player_id : str, channel):
	content = 'Welcome to the matrix_client. This is your command line. To see all commands, type \"**.help**\"\n'
	content = content + f'Your account ID is {player_id}. All channels ending with {player_id} are only visible to you.\n'
	content = content + 'In all other channels, your posts will be shown under your current **handle**.'
	await channel.send(content)

	content = '=== **HANDLES** ===\n'
	content = content + 'You can create and switch handles freely using the following commands:\n'
	content = content + '\n'
	content = content + '  **.handle <new_handle>**\n'
	content = content + '  Switch to handle - if it does not already exist, it will be created for you.\n'
	content = content + '  Regular handles cannot be deleted, but you can just abandon it if you don\'t need it.\n'
	content = content + '\n'
	content = content + '  **.handle**\n'
	content = content + '  Show you what your current handle is.\n'
	content = content + '\n'
	content = content + '  **.burner <new_handle>**\n'
	content = content + '  Switch to a burner handle - if it does not already exist, it will be created for you.\n'
	content = content + '\n'
	content = content + '  **.burn <burner_handle>**\n'
	content = content + '  Destroy a burner handle forever.\n'
	content = content + '  While a burner handle is active, it can possibly be traced.\n'
	content = content + '  After burning it, its ownership cannot be traced.\n'
	content = content + '\n '
	await channel.send(content)

	content = '=== **MONEY** ===\n'
	content = content + 'Each handle (regular and burner) has its own balance (money). Commands related to money:\n'
	content = content + '\n'
	content = content + '  **.balance**\n'
	content = content + '  Show the current balance of all handles you control.\n'
	content = content + '\n'
	content = content + '  **.collect**\n'
	content = content + '  Transfer all money from all handles you control to the one you are currently using.\n'
	content = content + '\n'
	content = content + '  **.pay <recipient> <amount>**\n'
	content = content + '  Transfer money from your current handle to the recipient.\n'
	content = content + '  You can of course use this to transfer money to another handle that you also own.\n'
	content = content + '\n'
	content = content + '  Note: when a burner handle is destroyed, any money on it will be transferred to your active handle.\n'
	content = content + '  Money transfer can be traced, even from burners.\n'
	content = content + '\n'
	await channel.send(content)

	content = '=== **REACTIONS** ===\n'
	content = '  You can also send money by reacting to messages. '
	content = content + 'Adding the following reactions to a message will transfer the corresponding amount of money:\n'
	for emoji, amount in reactions.reactions_worth_money.items():
		content = f'{content}  {emoji} = {coin}{amount}\n'

	await channel.send(content)

def get_cmd_line_channels_for_handles(handles : List[str]):
	actor_set = set() # Use a set to weed out duplicates
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


def get_cmd_line_channel_for_handle(handle : Handle):
	actor : Actor = actors.get_actor_for_handle(handle)
	if actor is not None:
		return get_cmd_line_channel(actor.actor_id)

def get_cmd_line_channel(player_id : str):
	data : PlayerData = read_player_data(player_id)
	if data is not None:
		return channels.get_discord_channel(data.cmd_line_channel_id)


# Shops

def add_shop(player_id : str, shop_id : str):
	player : PlayerData = read_player_data(player_id)
	if shop_id not in player.shops:
		player.shops.append(shop_id)
		store_player_data(player)

def remove_shop(player_id : str, shop_id : str):
	player : PlayerData = read_player_data(player_id)
	if player is not None and shop_id in player.shops:
		player.shops = [s for s in player.shops if s != shop_id]
		store_player_data(player)

def get_shops(player_id : str):
	return read_player_data(player_id).shops


# Groups

def add_group(player_id : str, group_id : str):
	player : PlayerData = read_player_data(player_id)
	print(f'Trying to add {player_id} to {group_id}; existing groups are {player.groups}')
	if player is not None and group_id not in player.groups:
		player.groups.append(group_id)
		store_player_data(player)


def remove_group(player_id : str, group_id : str):
	player : PlayerData = read_player_data(player_id)
	if player is not None and group_id in player.groups:
		player.groups = [g for g in player.groups if g != group_id]
		store_player_data(player)



async def is_gm(player_id : str):
	if player_exists(player_id):
		member = await server.get_member_from_nick(player_id)
		return server.check_member_has_role(member, [gm_role_name])

async def is_admin(player_id : str):
	if player_exists(player_id):
		member = await server.get_member_from_nick(player_id)
		return server.check_member_has_role(member, [admin_role_name])

async def is_gm_or_admin(player_id : str):
	if player_exists(player_id):
		member = await server.get_member_from_nick(player_id)
		print(f'Checking if {player_id} is gm or admin')
		return server.check_member_has_role(member, [gm_role_name, admin_role_name])