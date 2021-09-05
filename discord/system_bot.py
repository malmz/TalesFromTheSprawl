# bot.py
import os
import random
import discord
import asyncio

from configobj import ConfigObj

from discord.ext import commands
from dotenv import load_dotenv

# Custom imports
import handles
import channels
import posting
import reactions
import actors
import players
import finances
import custom_types
import chats
import server
import shops
import groups
import player_setup
import scenarios
import game
import artifacts
import admin
from common import coin


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
guild_name = os.getenv('GUILD_NAME')

intents = discord.Intents.default()
intents.members = True

# Change only the no_category default string
help_command = commands.DefaultHelpCommand(
    no_category = 'Commands'
)
bot = commands.Bot(
    command_prefix='.',
    intents=intents,
    help_command = help_command
)

guild = None

# Below cogs represents our folder our cogs are in. Following is the file name. So 'meme.py' in cogs, would be cogs.meme
# Think of it like a dot path import
initial_extensions = ['handles', 'finances', 'admin', 'chats', 'shops']

# Here we load our extensions(cogs) listed above in [initial_extensions].
if __name__ == '__main__':
    for extension in initial_extensions:
        bot.load_extension(extension)

@bot.event
async def on_ready():
    global guild
    global guild_name
    clear_all = False
    guild = discord.utils.find(lambda g: g.name == guild_name, bot.guilds)
    await server.init(bot, guild)
    await handles.init(clear_all)
    await actors.init(guild, clear_all=clear_all)
    await players.init(guild, clear_all=clear_all)
    await channels.init()
    finances.init_finances()
    await chats.init(clear_all=clear_all)
    await shops.init(guild, clear_all=clear_all)
    await groups.init(guild, clear_all=clear_all)
    artifacts.init(clear_all=clear_all)
    print('Initialization complete.')
    report = game.start_game()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.BadArgument) and 'Converting to "int" failed for parameter "amount"' in str(error):
        await ctx.send("Error: amount must be an integer greater than 0.")
    elif isinstance(error, commands.errors.BadArgument) and 'Converting to "int" failed for parameter "price"' in str(error):
        await ctx.send("Error: price must be an integer greater than 0.")
    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.send("Error: that is not a known command.")
    else:
        await ctx.send("Error: unknown system error. Contact administrator.")
        raise(error)

async def swallow(message, alert=True):
    await message.delete()
    if alert:
        await message.channel.send(
            'You cannot do that here. Try it in your #cmd_line instead.',
            delete_after=5)


# General message processing (reposting for anonymity/pseudonymity)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        # Never react to bot's own message to avoid loops
        return

    if channels.is_offline_channel(message.channel):
        # No bot shenanigans in the off channel
        return

    if not game.can_process_messages():
        await swallow(message, alert=False)
        return

    if (channels.is_cmd_line(message.channel.name)
        or channels.is_chat_hub(message.channel.name)
        ):
        await bot.process_commands(message)
        return        

    if channels.is_anonymous_channel(message.channel):
        await posting.process_open_message(message, True)
        return

    if channels.is_pseudonymous_channel(message.channel):
        await posting.process_open_message(message)

    if channels.is_chat_channel(message.channel):
        await chats.process_message(message)



# General reaction handling

@bot.event
async def on_raw_reaction_add(payload):
    channel = await bot.fetch_channel(payload.channel_id)
    if payload.user_id == bot.user.id:
        # Don't act on bot's own reactions to avoid loops
        return

    if channels.is_offline_channel(channel):
        # No bot shenanigans in the off channels
        return

    await reactions.process_reaction_add(payload.message_id, payload.user_id, channel, payload.emoji)

# New players

@bot.event
async def on_member_join(member):
    return await players.create_player(member)



# TODO: Fix the .help command:
# - Only show the commands that should be visible to the player
# - Group them by category, not alphabetically



# TODO: create GM-only cog

@bot.command(name='add_known_handle', help='Admin-only function to add a known handle, before the player joins the server.')
@commands.has_role('gm')
async def add_known_handle_command(ctx, handle_id : str):
    if handle_id is None:
        await ctx.send('Error: provide a handle')
    else:
        player_setup.add_known_handle(handle_id)
        await ctx.send(f'Added entry for {handle_id}. Please update its contents manually by editing the file.')



@bot.command(name='run_scenario', help='GM-only: run a scenario.')
@commands.has_role('gm')
async def run_scenario_command(ctx, name : str=None):
    if not channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return
    report = await scenarios.run_scenario(name)
    if report is not None:
        await ctx.send(report)


@bot.command(name='create_scenario', help='GM-only: create a basic scenario.')
@commands.has_role('gm')
async def create_scenario_command(ctx, name : str=None):
    if not channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return
    report = await scenarios.create_scenario(name)
    if report is not None:
        await ctx.send(report)



@bot.command(name='create_artifact', help='GM-only: create an artifact.')
@commands.has_role('gm')
async def create_artifact_command(ctx, name : str=None, content : str=None):
    if not channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return
    report = artifacts.create_artifact(name, content)
    if report is not None:
        await ctx.send(report)


@bot.command(name='connect', help='Connect to device or remote server.')
async def connect_command(ctx, name : str=None, code : str=None):
    if not channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return
    report = artifacts.access_artifact(name, code)
    if report is not None:
        await ctx.send(report)

@bot.command(name='login', help='Connect to device or remote server. Alias: \".connect\"')
async def connect_command(ctx, name : str=None, code : str=None):
    if not channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return
    report = artifacts.access_artifact(name, code)
    if report is not None:
        await ctx.send(report)



bot.run(TOKEN)
