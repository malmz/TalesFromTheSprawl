import discord
import asyncio

from constants import system_role_name, admin_role_name

system_role = None
admin_role = None
guild = None

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
			guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
			player_role: discord.PermissionOverwrite(read_messages=True),
			system_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
			admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
		}
	else:
		overwrites = {
			guild.default_role: discord.PermissionOverwrite(read_messages=False),
			player_role: discord.PermissionOverwrite(read_messages=True),
			system_role: discord.PermissionOverwrite(read_messages=True),
			admin_role: discord.PermissionOverwrite(read_messages=True)
		}
	return overwrites

def get_guild():
	return guild