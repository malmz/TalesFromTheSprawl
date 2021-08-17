import channels
import handles
import reactions
import common
import server
import actors

from common import coin, highest_ever_index, player_personal_role_start
from custom_types import PlayerData

import discord
import asyncio
from configobj import ConfigObj


players = ConfigObj('players.conf')
players_input = ConfigObj('players_input.conf')

user_id_mappings_index = '___user_id_to_player_id'

# TODO: loop through all users, find their player_ids and re-map personal channels if not available
async def init(bot, guild, clear_all=False):
	if not user_id_mappings_index in players or clear_all:
		players[user_id_mappings_index] = {}
	if not highest_ever_index in players[user_id_mappings_index] or clear_all:
		players[user_id_mappings_index][highest_ever_index] = str(player_personal_role_start)
	if clear_all:
		for player_id in get_all_players():
			del players[player_id]
		#await channels.delete_all_personal_channels(bot)
		#await handles.clear_all_handles()
		# TODO: only clear out players, not shops

	players.write()

async def initialise_all_users(guild):
	task_list = (asyncio.create_task(create_player(m)) for m in guild.members if not m.bot)
	await asyncio.gather(*task_list)

def get_all_players():
	for player in players:
		if not player in [highest_ever_index, user_id_mappings_index]:
			yield player

def player_exists(player_id : str):
	return player_id in get_all_players()

def is_player(actor_id : str):
	return player_id in get_all_players()

def store_player_data(player_data : PlayerData):
	players[player_data.player_id] = player_data.to_string()
	players.write()

def read_player_data(player_id : str):
	if player_id in players:
		return PlayerData.from_string(players[player_id])


# TODO: check where get_player_id is used; perhaps they want to also grab the Actor object.

def get_player_id(user_id : str, expect_to_find=True):
	if not user_id in players[user_id_mappings_index]:
		if expect_to_find:
			raise RuntimeError(f'User {user_id} has not been initialized as a player. Fix that first.')
		else:
			return None
	return players[user_id_mappings_index][user_id];


async def create_player(member):
	user_id = str(member.id)
	existing_player_id = get_player_id(user_id, expect_to_find=False)
	if existing_player_id is not None:
		return f'Error: Could not create player for member {user_id}, since they already have player_id {existing_player_id}.'

	prev_highest = int(players[user_id_mappings_index][highest_ever_index])
	new_player_id = str(prev_highest + 1)

	# A player is a type of actor, so we start by creating an actor for this member/user
	actor : actors.Actor = await actors.create_new_actor(member.guild, new_player_id)
	role = actors.get_actor_role(member.guild, actor.actor_id)
	
	players[user_id_mappings_index][user_id] = new_player_id
	players[user_id_mappings_index][highest_ever_index] = new_player_id
	players.write()

	# Create personal command line channels for player
	overwrites = server.generate_overwrites_own_new_private_channel(role)

	cmd_line_channel = await channels.create_personal_channel(
		member.guild,
		overwrites,
		channels.get_cmd_line_name(new_player_id)
	)

	# Send welcome messages before adding the role -> avoid spamming notifications
	await send_startup_message_cmd_line(member, new_player_id, cmd_line_channel)

	# Edit user (change nick and add role):
	base_nick = 'u' + new_player_id
	#await member.guild.create
	try:
		new_roles = member.roles
		new_roles.append(role)
		all_players_role = server.get_all_players_role()
		if all_players_role not in new_roles:
			new_roles.append(server.get_all_players_role())
		await member.edit(nick = base_nick, roles=new_roles)
	except discord.Forbidden:
		print(f'Probably tried to edit server owner, which doesn\'t work. Please add role {new_player_id} to user {member.name}.')

	# Move to actors, and pass in the "actor_name" e.g. "u2702"
	handles.init_handles_for_actor(new_player_id, base_nick)
	player_data = PlayerData(new_player_id, cmd_line_channel.id)
	store_player_data(player_data)

async def send_startup_message_cmd_line(member, player_id : str, channel):
	content = 'Welcome to the matrix_client. This is your command line. To see all commands, type \"**.help**\"\n'
	content = content + f'Your account ID is {member.nick}. All channels ending with {player_id} are only visible to you.\n'
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


def get_cmd_line_channel_for_handle(handle : str):
	actor : Actor = actors.get_actor_for_handle(handle)
	if actor is not None:
		return get_cmd_line_channel(actor.actor_id)

def get_cmd_line_channel(player_id : str):
	data : PlayerData = read_player_data(player_id)
	if data is not None:
		return channels.get_discord_channel(data.cmd_line_channel_id)

