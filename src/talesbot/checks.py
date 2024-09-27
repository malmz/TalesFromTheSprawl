import discord

from talesbot import gm

is_gm = discord.app_commands.checks.has_role(gm.role_name)
