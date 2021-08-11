import common_channels
import handles
import reactions

import discord
from configobj import ConfigObj

players = ConfigObj('players.conf')
players_input = ConfigObj('players_input.conf')

highest_ever_index = '___highest_ever'

system_role_name = 'system'
system_role = None

def init(bot, guild):
	global system_role
	system_role = discord.utils.find(lambda role: role.name == system_role_name, guild.roles)
	if not 'player_ids' in players:
		players['player_ids'] = {}
	if not highest_ever_index in players['player_ids']:
		players['player_ids'][highest_ever_index] = '2701'
	players.write()


async def create_player(member):
	user_id = str(member.id)
	prev_highest = int(players['player_ids'][highest_ever_index])
	new_player_id = str(prev_highest + 1)
	players['player_ids'][user_id] = new_player_id
	players['player_ids'][highest_ever_index] = new_player_id
	players.write()

	# Create role for this user:
	role = await member.guild.create_role(name=new_player_id)

	# Create personal channels for user:
	category_personal = discord.utils.find(lambda cat: cat.name == common_channels.personal_category_name, member.guild.channels)
	overwrites = {
		member.guild.default_role: discord.PermissionOverwrite(read_messages=False),
		role: discord.PermissionOverwrite(read_messages=True),
		system_role: discord.PermissionOverwrite(read_messages=True)
	}
	cmd_line_channel_name = common_channels.get_cmd_line_name(new_player_id)
	cmd_line_channel = await member.guild.create_text_channel(cmd_line_channel_name, overwrites=overwrites, category=category_personal)
	common_channels.init_personal_channel(cmd_line_channel)
	# TODO: create other channels for user

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

	await send_startup_messages(member, new_player_id, cmd_line_channel)

	handles.init_handles_for_user(user_id, base_nick)

async def send_startup_messages(member, player_id : str, channel):
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
	content = content + '  Adding the following reactions to a message will transfer the corresponding amount of money:\n'
	for emoji, amount in reactions.reactions_worth_money.items():
		content = content + '  ' + emoji + ' = ¥' + str(amount)

	await channel.send(content)

def get_cmd_line_channel(guild, user_id : str):
	player_id = players['player_ids'][user_id]
	cmd_line_channel_name = common_channels.get_cmd_line_name(player_id)
	cmd_line_channel_id = common_channels.get_channel_id(cmd_line_channel_name)
	return guild.get_channel(cmd_line_channel_id)
