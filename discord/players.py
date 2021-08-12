import channels
import handles
import reactions
import finances
import constants
from constants import highest_ever_index, player_ids_index, system_role_name
from custom_types import Transaction

import discord
import asyncio
from configobj import ConfigObj


players = ConfigObj('players.conf')
players_input = ConfigObj('players_input.conf')

system_role = None

finance_statement_index = '___finance_statement_msg_id'

def init(bot, guild):
	global system_role
	system_role = discord.utils.find(lambda role: role.name == system_role_name, guild.roles)
	if not player_ids_index in players:
		players[player_ids_index] = {}
	if not highest_ever_index in players[player_ids_index]:
		players[player_ids_index][highest_ever_index] = '2701'
	players.write()

async def create_personal_channel(member, overwrites, channel_name):
	category_personal = discord.utils.find(lambda cat: cat.name == channels.personal_category_name, member.guild.channels)
	overwrites = {
		member.guild.default_role: discord.PermissionOverwrite(read_messages=False),
		role: discord.PermissionOverwrite(read_messages=True),
		system_role: discord.PermissionOverwrite(read_messages=True)
	}
	channel_name = channels.get_cmd_line_name(player_id)
	channel = await member.guild.create_text_channel(channel_name, overwrites=overwrites, category=category_personal)
	channels.init_personal_channel(channel)
	return channel


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
	overwrites = {
		member.guild.default_role: discord.PermissionOverwrite(read_messages=False),
		role: discord.PermissionOverwrite(read_messages=True),
		system_role: discord.PermissionOverwrite(read_messages=True)
	}

	overwrites_finance = {
		member.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
		role: discord.PermissionOverwrite(read_messages=True),
		system_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
	}

	cmd_line_channel = await channels.create_personal_channel(
		member,
		overwrites,
		channels.get_cmd_line_name(new_player_id)
	)
	inbox_channel = await channels.create_personal_channel(
		member,
		overwrites,
		channels.get_inbox_name(new_player_id)
	)
	outbox_channel = await channels.create_personal_channel(
		member,
		overwrites,
		channels.get_outbox_name(new_player_id)
	)
	finances_channel = await channels.create_personal_channel(
		member,
		overwrites_finance,
		channels.get_finance_name(new_player_id)
	)

	## TODO: give the new role read permission in various locked channels, e.g. anon

	# Edit user (change nick and add role):
	base_nick = 'u' + new_player_id
	#await member.guild.create
	try:
		print(f'{member.roles}')
		new_roles = member.roles
		new_roles.append(role)
		print(f'{new_roles[0]}, {new_roles[1]}')
		await member.edit(nick = base_nick, roles=new_roles)
	except discord.Forbidden:
		print(f'Probably tried to edit server owner, wont\'t work')

	# TODO: send welcome message in cmd_line

	task1 = asyncio.create_task(send_startup_message_cmd_line(member, new_player_id, cmd_line_channel))

	task2 = asyncio.create_task(
		send_startup_message_inbox(
			inbox_channel,
			get_clickable_channel_ref(member.guild, outbox_channel)
		)
	)
	task3 = asyncio.create_task(
		send_startup_message_outbox(
			outbox_channel,
			get_clickable_channel_ref(member.guild, inbox_channel)
		)
	)
	task4 = asyncio.create_task(send_startup_message_finance(finances_channel))
	await task1
	await task2
	await task3
	await task4

	handles.init_handles_for_user(user_id, base_nick)

def get_clickable_channel_ref(guild, channel):
	return f'<#{channel.id}>'

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

async def send_startup_message_inbox(channel, outbox_channel_name):
	content = 'This is your inbox. Private messages from other users will appear here.\n'
	content = content + f'Note: you cannot respond here. To respond, you have to send a message from your outbox: {outbox_channel_name}.\n'
	await channel.send(content)

async def send_startup_message_outbox(channel, inbox_channel_name):
	content = 'This is your outbox. Think of it as an email client.\n'
	content = content + 'Send messages by typing \'.message <recipient> \"message\"\', e.g. \'.message Shadow_Weaver \"Oi chummer!\"\'.\n'
	content = content + f'The message will show up in recipient\'s inbox. You have your inbox in {inbox_channel_name}.'
	await channel.send(content)

async def send_startup_message_finance(channel):
	content = 'This is your financial record.\n'
	content = content + 'A record of every transaction will appear here. You cannot send anything in this channel.'
	await channel.send(content)

async def update_financial_statement(channel, user_id : str):
	player_id = players[player_ids_index][user_id]
	if not player_id in players:
		players[player_id] = {}
	if finance_statement_index in players[player_id]:
		msg_id = players[player_id][finance_statement_index]
		message = await channel.fetch_message(msg_id)
		await message.delete()

	report = finances.get_all_handles_balance_report(user_id)
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
				payer_status.user_id,
				finances.generate_record_collected(transaction),
				transaction.last_in_sequence
			)
		elif recip_status.exists:
			# Both payer and recip are normal handles
			if payer_status.user_id == recip_status.user_id:
				# Special case: payer and recip are the same
				await write_financial_record(
					guild,
					payer_status.user_id,
					finances.generate_record_self_transfer(transaction),
					transaction.last_in_sequence
				)
			else:
				await asyncio.create_task(
					write_financial_record(
						guild,
						payer_status.user_id,
						finances.generate_record_payer(transaction),
						transaction.last_in_sequence
					)
				)
				await asyncio.create_task(
					write_financial_record(
						guild,
						recip_status.user_id,
						finances.generate_record_recip(transaction),
						transaction.last_in_sequence
					)
				)
		else:
			# Only payer exists, not recip:
			await write_financial_record(guild,
				payer_status.user_id,
				finances.generate_record_payer(transaction),
				transaction.last_in_sequence
			)
	elif recip_status.exists:
		# Only recip exists, not payer
		# Special case: payer is the collection from other accounts
		if transaction.payer == constants.transaction_collected:
			await write_financial_record(
				guild,
				recip_status.user_id,
				finances.generate_record_collector(transaction),
				transaction.last_in_sequence
			)
		else:
			await write_financial_record(guild, recip_status.user_id, finances.generate_record_recip(transaction), transaction.last_in_sequence)


async def write_financial_record(guild, user_id : str, content : str, last_in_sequence : bool):
	player_id = players[player_ids_index][user_id]
	channel = get_finance_channel_for_user(guild, user_id)
	await asyncio.create_task(channel.send(content))
	if last_in_sequence:
		await asyncio.create_task(update_financial_statement(channel, user_id))


def get_cmd_line_channel_for_handle(guild, handle : str):
	status : handles.HandleStatus = handles.get_handle_status(handle)
	if status.exists:
		player_id = players[player_ids][status.user_id]
		return channels.get_cmd_line_channel(guild, player_id)
	else:
		return None

def get_inbox_channel_for_handle(guild, handle : str):
	status : handles.HandleStatus = handles.get_handle_status(handle)
	if status.exists:
		player_id = players[player_ids_index][status.user_id]
		return channels.get_inbox_channel(guild, player_id)
	else:
		return None

def get_finance_channel_for_handle(guild, handle : str):
	status : handles.HandleStatus = handles.get_handle_status(handle)
	if status.exists:
		return get_finance_channel_for_user(guild, status.user_id)
	else:
		return None

def get_finance_channel_for_user(guild, user_id : str):
	player_id = players[player_ids_index][user_id]
	return channels.get_finance_channel(guild, player_id)
