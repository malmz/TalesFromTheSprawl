import common_channels
import handles
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

	handles.init_handles_for_user(user_id, base_nick)

def get_cmd_line_channel(guild, user_id : str):
	player_id = players['player_ids'][user_id]
	cmd_line_channel_name = common_channels.get_cmd_line_name(player_id)
	cmd_line_channel_id = common_channels.get_channel_id(cmd_line_channel_name)
	return guild.get_channel(cmd_line_channel_id)
