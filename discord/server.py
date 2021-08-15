import discord
import asyncio

from constants import system_role_name, admin_role_name

system_role = None
admin_role = None
guild = None

read_only_base = discord.PermissionOverwrite(read_messages=False, send_messages=False)
normal_base = discord.PermissionOverwrite(read_messages=False)
normal_access = discord.PermissionOverwrite(read_messages=True)
super_access = discord.PermissionOverwrite(read_messages=True, send_messages=True)

def init(bot, current_guild):
	global system_role
	global admin_role
	global guild
	guild = current_guild
	system_role = discord.utils.find(lambda role: role.name == system_role_name, guild.roles)
	admin_role = discord.utils.find(lambda role: role.name == admin_role_name, guild.roles)

def generate_overwrites_private_channel(player_role, read_only : bool=False):
	if read_only:
		overwrites = {
			guild.default_role: read_only_base,
			player_role: normal_access,
			system_role: super_access,
			admin_role: super_access
		}
	else:
		overwrites = {
			guild.default_role: normal_base,
			player_role: normal_access,
			system_role: super_access,
			admin_role: super_access
		}
	return overwrites

def generate_base_overwrites_new_channel(read_only : bool=False):
	if read_only:
		overwrites = {
			guild.default_role: read_only_base,
			system_role: super_access,
			admin_role: super_access
		}
	else:
		overwrites = {
			guild.default_role: normal_base,
			system_role: super_access,
			admin_role: super_access
		}
	return overwrites

def get_guild():
	return guild