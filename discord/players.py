import common_channels
import handles
import discord
from configobj import ConfigObj

players = ConfigObj('players.conf')
players_input = ConfigObj('players_input.conf')

highest_ever_index = '___highest_ever'
cmd_line_base = 'cmd_line_'
inbox_base = 'inbox_'
outbox_base = 'outbox_'
finance_base = 'finance_'
daemon_base = 'daemon_'
private_base = 'private_chats_'

def init(bot):
	if not 'player_ids' in players:
		players['player_ids'] = {}
	if not highest_ever_index in players['player_ids']:
		players['player_ids'][highest_ever_index] = '2701'
	players.write()

def get_cmd_line_name(player_id : str):
	return cmd_line_base + player_id

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
	category_personal = discord.utils.find(lambda cat: cat.name == 'Personal Account', member.guild.channels)
	overwrites = {
		member.guild.default_role: discord.PermissionOverwrite(read_messages=False),
		role: discord.PermissionOverwrite(read_messages=True)
	}
	cmd_line_channel_name = get_cmd_line_name(new_player_id)
	cmd_line_channel = await member.guild.create_text_channel(cmd_line_channel, overwrites=overwrites, category=category_personal)
	# TODO: init_channel data in conf?
	# TODO: create other channels for user

	# Edit user (change nick and add role):
	base_nick = 'u' + new_player_id
	#await member.guild.create
	try:
		await member.edit(nick = base_nick)
		# TODO: give role to user
	except discord.Forbidden:
		print(f'Probably tried to edit server owner, wont\'t work')

	# TODO: send welcome message in cmd_line



	handles.init_handles_for_user(user_id, base_nick)