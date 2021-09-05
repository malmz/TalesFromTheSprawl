import actors
import players
import groups
import player_setup
import scenarios
import artifacts
import channels

from discord.ext import commands
import discord
import asyncio

### Module gm.py
# This module holds the gm cog, which is used to set up in-game content

# TODO: grab the name of the GM role from env file


class GmCog(commands.Cog, name='admin'):
	"""GM-only commands, hidden by default. To view documentation, use \"help <command>\". The commands are:
	add_known_handle, create_scenario, run_scenario, create_artifact"""
	def __init__(self, bot):
		self.bot = bot
		self._last_member = None

	# GM-only commands for setting up in-game content.

	@commands.command(
		name='add_known_handle',
		brief='GM-only. Add a player\'s handle.',
		help=(
			'Add a player\'s handle before they join the server. ' +
			'When a player claims the given handle, their initial data ' +
			'(aliases, money, groups etc) will be set up automatically.'
			),
		hidden=True
		)
	@commands.has_role('gm')
	async def add_known_handle_command(self, ctx, handle_id : str):
		if handle_id is None:
			await ctx.send('Error: provide a handle')
		else:
			player_setup.add_known_handle(handle_id)
			await ctx.send(f'Added entry for {handle_id}. Please update its contents manually by editing the file.')



	@commands.command(
		name='run_scenario',
		help='GM-only. Run a scenario.',
		hidden=True)
	@commands.has_role('gm')
	async def run_scenario_command(self, ctx, name : str=None):
		if not channels.is_cmd_line(ctx.channel.name):
			await swallow(ctx.message);
			return
		report = await scenarios.run_scenario(name)
		if report is not None:
			await ctx.send(report)

	@commands.command(
		name='create_scenario',
		help='GM-only. Create a basic scenario.',
		hidden=True)
	@commands.has_role('gm')
	async def create_scenario_command(self, ctx, name : str=None):
		if not channels.is_cmd_line(ctx.channel.name):
			await swallow(ctx.message);
			return
		report = await scenarios.create_scenario(name)
		if report is not None:
			await ctx.send(report)



	@commands.command(
		name='create_artifact',
		brief='GM-only. Create an artifact.',
		help=(
			'Create an artifact, which is any sort of digital content that players can access ' +
			'using some sort of username/password setup. Examples include encrypted cloud storage ' +
			'(where the player finds the user/pw) and physical devices that the player \"connects\" to ' +
			'(by entering a device ID, \"port number\" or similar which is printed on the physical thing).'
			),
		hidden=True
		)
	@commands.has_role('gm')
	async def create_artifact_command(self, ctx, name : str=None, content : str=None):
		if not channels.is_cmd_line(ctx.channel.name):
			await swallow(ctx.message);
			return
		report = artifacts.create_artifact(name, content)
		if report is not None:
			await ctx.send(report)



def setup(bot):
	bot.add_cog(GmCog(bot))