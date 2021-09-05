import actors
import players

from discord.ext import commands
import discord
import asyncio

### Module admin.py
# This module holds the admin cog, which is used to



class AdminCog(commands.Cog, name='admin'):
	"""Admin-only commands, hidden by default. To view documentation, use \"help <command>\". The commands are:
	init_all_players, fake_join, fake_join_name, fake_join_nick, clear_all_players, clear_all_actors, clear_actor, ping"""
	def __init__(self, bot):
		self.bot = bot
		self._last_member = None

	# Admin-only commands for testing etc.

	@commands.command(
		name='init_all_players',
		help='Admin-only. Initialise all current members of the server as players.',
		hidden=True
		)
	@commands.has_role('gm')
	async def init_all_players_command(self, ctx):
		await players.initialise_all_users()
		await ctx.send('Done.')

	@commands.command(
		name='fake_join',
		help='Admin-only. Initialise a user as a player.',
		hidden=True)
	@commands.has_role('gm')
	async def fake_join_command(self, ctx, user_id):
		member_to_fake_join = await ctx.guild.fetch_member(user_id)
		if member_to_fake_join is None:
			await ctx.send(f'Failed: member with user_id {user_id} not found.')
		else:
			report = await players.create_player(member_to_fake_join)
			if report is None:
				report = "Done."
			await ctx.send(report)

	@commands.command(
		name='fake_join_name',
		help='Admin-only. Initialise a user as a player (based on discord name).',
		hidden=True)
	@commands.has_role('gm')
	async def fake_join_name_command(self, ctx, name : str):
		members = await ctx.guild.fetch_members(limit=100).flatten()
		member_to_fake_join = discord.utils.find(lambda m: m.name == name, members)
		if member_to_fake_join is None:
			await ctx.send(f'Failed: member with name {name} not found.')
		else:
			report = await players.create_player(member_to_fake_join)
			if report is None:
				report = "Done."
			await ctx.send(report)

	@commands.command(
		name='fake_join_nick',
		help='Admin-only. Initialise a user as a player (based on server nick).',
		hidden=True)
	@commands.has_role('gm')
	async def fake_join_nick_command(self, ctx, nick : str):
		member_to_fake_join = await server.get_member_from_nick(nick)
		if member_to_fake_join is None:
			await ctx.send(f'Failed: member with nick {nick} not found.')
		else:
			report = await players.create_player(member_to_fake_join)
			if report is None:
				report = "Done."
			await ctx.send(report)

	@commands.command(
		name='clear_all_players',
		help='Admin-only. De-initialise all players.',
		hidden=True)
	@commands.has_role('gm')
	async def clear_all_players_command(self, ctx):
		await players.init(ctx.guild, clear_all=True)
		try:
			await ctx.send('Done.')
		except discord.errors.NotFound:
			print('Cleared all players. Could not send report because channel is missing – '
				+'the command was probably given in a player-only command line that was deleted.')

	@commands.command(
		name='clear_all_actors',
		help='Admin-only: de-initialise all actors (players and shops).',
		hidden=True)
	@commands.has_role('gm')
	async def clear_all_actors_command(self, ctx):
		await actors.init(ctx.guild, clear_all=True)
		try:
			await ctx.send('Done.')
		except discord.errors.NotFound:
			print('Cleared all actors. Could not send report because channel is missing – '
				+'the command was probably given in a player-only command line that was deleted.')

	@commands.command(
		name='clear_actor',
		help='Admin-only: de-initialise an actor (player or shop).',
		hidden=True)
	@commands.has_role('gm')
	async def clear_actor_command(self, ctx, actor_id : str):
		report = await actors.clear_actor(ctx.guild, actor_id)
		try:
			await ctx.send(report)
		except discord.errors.NotFound:
			print(f'Cleared actor {actor_id}. Could not send report because channel is missing – '
				+'the command was probably given in a player-only command line that was deleted.')
	
	@commands.command(
		name='ping',
		help='Admin-only. Send a ping to a player\'s cmd_line channel.',
		hidden=True)
	@commands.has_role('gm')
	async def ping_command(self, ctx, player_id : str):
		channel = players.get_cmd_line_channel(player_id)
		if channel != None:
			await channel.send(f'Testing ping for {player_id}')
		else:
			await ctx.send(f'Error: could not find the command line channel for {player_id}')

def setup(bot):
    bot.add_cog(AdminCog(bot))