import discord
import asyncio

from constants import system_role_name, admin_role_name, all_players_role_name, gm_role_name

system_role = None
admin_role = None
all_players_role = None
gm_role = None
guild = None

no_access = discord.PermissionOverwrite(read_messages=False, send_messages=False)
normal_access = discord.PermissionOverwrite(read_messages=True) # Will get send access depending on all_players_role settings for this channel
super_access = discord.PermissionOverwrite(read_messages=True, send_messages=True)

private_read_only_base = no_access
# A little weird to set read=False send=True,
# but it means that anyone who does get read access will automatically also have send access
private_normal_base = discord.PermissionOverwrite(read_messages=False, send_messages=True)
public_read_only_base = discord.PermissionOverwrite(read_messages=True, send_messages=False)
public_normal_base = discord.PermissionOverwrite(read_messages=True, send_messages=True)

async def init(bot, current_guild):
	global system_role
	global admin_role
	global guild
	global all_players_role
	global gm_role
	guild = current_guild
	system_role = discord.utils.find(lambda role: role.name == system_role_name, guild.roles)
	admin_role = discord.utils.find(lambda role: role.name == admin_role_name, guild.roles)
	gm_role = discord.utils.find(lambda role: role.name == gm_role_name, guild.roles)
	all_players_role = discord.utils.find(lambda role: role.name == all_players_role_name, guild.roles)
	if all_players_role is None:
		print(f'Creating role with name {all_players_role_name}')
		all_players_role = await guild.create_role(name=all_players_role_name)

def get_all_players_role():
	return all_players_role

def generate_overwrites_own_private_channel(player_role):
	return {player_role: normal_access}

def generate_overwrites_own_new_private_channel(player_role, read_only : bool=False):
	return (
		{**generate_base_overwrites(private=True, read_only=read_only),
		**generate_overwrites_own_private_channel(player_role)
		})

def generate_base_overwrites(private : bool, read_only : bool):
	if private:
		access_level = private_read_only_base if read_only else private_normal_base
	else:
		access_level = public_read_only_base if read_only else public_normal_base		
	return (
		{guild.default_role: no_access,
		all_players_role: access_level,
		system_role: super_access,
		admin_role: super_access,
		gm_role : normal_access if not private else no_access
		})

def get_guild():
	return guild