import channels
import handles
import reactions
import finances
import constants
import server

from constants import highest_ever_index, player_ids_index
from custom_types import Transaction

import discord
import asyncio
from configobj import ConfigObj
import re


players = ConfigObj('players.conf')
players_input = ConfigObj('players_input.conf')

personal_role_regex = re.compile(f'^2[0-9][0-9][0-9]$')

finance_statement_index = '___finance_statement_msg_id'

# TODO: loop through all users, find their player_ids and re-map personal channels if not available
async def init(bot, guild, clear_all=False):
	if not player_ids_index in players or clear_all:
		players[player_ids_index] = {}
	if not highest_ever_index in players[player_ids_index] or clear_all:
		players[player_ids_index][highest_ever_index] = '2701'
	if clear_all:
		for player_id in get_all_players():
			del players[player_id]
		await channels.delete_all_personal_channels(bot)
		handles.clear_all_handles()
	await delete_all_player_roles(guild, spare_used=(not clear_all))

	players.write()

async def initialise_all_users(guild):
	task_list = (asyncio.create_task(create_player(m)) for m in guild.members if not m.bot)
	await asyncio.gather(*task_list)

async def delete_all_player_roles(guild, spare_used : bool):
	task_list = (asyncio.create_task(delete_if_player_role(r, spare_used)) for r in guild.roles)
	await asyncio.gather(*task_list)

async def delete_if_player_role(role, spare_used : bool):
	matches = re.search(personal_role_regex, role.name)
	if matches != None:
		if not spare_used or len(role.members) == 0:
			print(f'Deleting unused role with name {role.name}')
			await role.delete()

def get_all_players():
	for player in players:
		if not player in [highest_ever_index, player_ids_index]:
			yield player

def get_player_id(user_id : str):
	if not user_id in players[player_ids_index]:
		raise RuntimeError(f'User {user_id} has not been initialized as a player. Fix that first.')
	return players[player_ids_index][user_id];

def get_player_role(guild, player_id : str):
	return discord.utils.find(lambda role: role.name == player_id, guild.roles)

# TODO: this could perhaps be refactored to use the overwrite generation functions in server.py
async def give_role_access(channel, role):
	await channel.set_permissions(role, read_messages=True)

async def give_player_access(guild, channel, player_id : str):
	role = get_player_role(guild, player_id)
	await give_role_access(channel, role)

async def create_player(member):
	user_id = str(member.id)
	prev_highest = int(players[player_ids_index][highest_ever_index])
	new_player_id = str(prev_highest + 1)
	players[player_ids_index][user_id] = new_player_id
	players[player_ids_index][highest_ever_index] = new_player_id
	players[new_player_id] = {}
	players.write()
	# Create role for this user:
	role = await member.guild.create_role(name=new_player_id)

	# Create personal channels for user:
	overwrites = server.generate_overwrites_own_new_private_channel(role)
	overwrites_finance = server.generate_overwrites_own_new_private_channel(role, read_only=True)

	cmd_line_creation = asyncio.create_task(channels.create_personal_channel(
		member.guild,
		overwrites,
		channels.get_cmd_line_name(new_player_id)
	))

	chat_hub_creation = asyncio.create_task(channels.create_personal_channel(
		member.guild,
		overwrites,
		channels.get_chat_hub_name(new_player_id)
	))

	finances_creation = asyncio.create_task(channels.create_personal_channel(
		member.guild,
		overwrites_finance,
		channels.get_finance_name(new_player_id)
	))

	[cmd_line_channel, chat_hub_channel, finances_channel] = (
		await asyncio.gather(cmd_line_creation, chat_hub_creation, finances_creation)
	)

	# This is a test:
	# Hopefully new players won't get notifications from chat_hub welcome message,
	# since it was sent before they got the role that allows them access
	await send_startup_message_chat_hub(chat_hub_channel)

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

	cmd_line_welcome = asyncio.create_task(send_startup_message_cmd_line(member, new_player_id, cmd_line_channel))
	finance_welcome = asyncio.create_task(send_startup_message_finance(finances_channel))
	await asyncio.gather(cmd_line_welcome, finance_welcome)

	handles.init_handles_for_player(new_player_id, base_nick)

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
		content = content + '  ' + emoji + ' = ¥' + str(amount) + '\n'

	await channel.send(content)

async def send_startup_message_finance(channel):
	content = 'This is your financial record.\n'
	content = content + 'A record of every transaction will appear here. You cannot send anything in this channel.'
	await channel.send(content)

async def send_startup_message_chat_hub(channel):
	content = 'This is your chat hub. All your chat connections will be visible here, even when the session itself is closed.\n '
	content = content + 'You can start new chats by typing \".chat <handle>\" or [NOT IMPLEMENTED YET] \".room <room_name>\".'
	await channel.send(content)

async def update_financial_statement(channel, player_id : str):
	if not player_id in players:
		raise RuntimeError(f'Player {player_id} has not been initialized correctly.')
	if finance_statement_index in players[player_id]:
		msg_id = players[player_id][finance_statement_index]
		message = await channel.fetch_message(msg_id)
		await message.delete()

	report = finances.get_all_handles_balance_report(player_id)
	content = '========================\n' + report

	new_message = await channel.send(content)
	players[player_id][finance_statement_index] = new_message.id
	players.write()

async def record_transaction(guild, transaction : Transaction):
	payer_status : handles.HandleStatus = handles.get_handle_status(transaction.payer)
	recip_status : handles.HandleStatus = handles.get_handle_status(transaction.recip)
	if payer_status.exists:
		# Special case: recip is a collector account
		if transaction.recip == constants.transaction_collector:
			await write_financial_record(
				guild,
				payer_status.player_id,
				finances.generate_record_collected(transaction),
				transaction.last_in_sequence
			)
		elif recip_status.exists:
			# Both payer and recip are normal handles
			if payer_status.player_id == recip_status.player_id:
				# Special case: payer and recip are the same
				await write_financial_record(
					guild,
					payer_status.player_id,
					finances.generate_record_self_transfer(transaction),
					transaction.last_in_sequence
				)
			else:
				await asyncio.create_task(
					write_financial_record(
						guild,
						payer_status.player_id,
						finances.generate_record_payer(transaction),
						transaction.last_in_sequence
					)
				)
				await asyncio.create_task(
					write_financial_record(
						guild,
						recip_status.player_id,
						finances.generate_record_recip(transaction),
						transaction.last_in_sequence
					)
				)
		else:
			# Only payer exists, not recip:
			await write_financial_record(guild,
				payer_status.player_id,
				finances.generate_record_payer(transaction),
				transaction.last_in_sequence
			)
	elif recip_status.exists:
		# Only recip exists, not payer
		# Special case: payer is the collection from other accounts
		if transaction.payer == constants.transaction_collected:
			await write_financial_record(
				guild,
				recip_status.player_id,
				finances.generate_record_collector(transaction),
				transaction.last_in_sequence
			)
		else:
			await write_financial_record(guild, recip_status.player_id, finances.generate_record_recip(transaction), transaction.last_in_sequence)


async def write_financial_record(guild, player_id : str, content : str, last_in_sequence : bool):
	channel = channels.get_finance_channel(guild, player_id)
	await asyncio.create_task(channel.send(content))
	if last_in_sequence:
		await asyncio.create_task(update_financial_statement(channel, player_id))


def get_cmd_line_channel_for_handle(guild, handle : str):
	status : handles.HandleStatus = handles.get_handle_status(handle)
	if status.exists:
		return channels.get_cmd_line_channel(guild, status.player_id)
	else:
		return None

def get_finance_channel_for_handle(guild, handle : str):
	status : handles.HandleStatus = handles.get_handle_status(handle)
	if status.exists:
		return channels.get_finance_channel(guild, status.player_id)
	else:
		return None

def get_chat_hub_channel_for_handle(guild, handle : str):
	status : handles.HandleStatus = handles.get_handle_status(handle)
	if status.exists:
		return channels.get_chat_hub_channel(guild, status.player_id)
	else:
		return None

