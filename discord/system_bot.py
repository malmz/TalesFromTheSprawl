# bot.py
import os
import random
import discord
import asyncio

from configobj import ConfigObj

from discord.ext import commands
from dotenv import load_dotenv
from collections import namedtuple

# Custom imports
import handles
import channels
import posting
import reactions
import players
import finances
import custom_types
import chats
import server


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

@bot.event
async def on_ready():
    global guild
    global guild_name
    guild = discord.utils.find(lambda g: g.name == guild_name, bot.guilds)
    server.init(bot, guild)
    await players.init(bot, guild, clear_all=False)
    await channels.init_channels(bot)
    #handles.init() #TODO: ensure that every user has a handle?
    finances.init_finances()
    await chats.init(bot, clear_all=False)
    print('Initialization complete.')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.BadArgument) and 'Converting to "int" failed for parameter "amount"' in str(error):
        await ctx.send("Error: amount must be an integer greater than 0.")
    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.send("Error: that is not a known command.")
    else:
        await ctx.send("Error: unknown system error. Contact administrator.")
        raise(error)

async def swallow(message):
    await message.delete()
    alert = await message.channel.send('You cannot do that here. Try it your #cmd_line instead.')
    await asyncio.sleep(5)
    await alert.delete()


# General message processing (reposting for anonymity/pseudonymity)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        # Never react to bot's own message to avoid loops
        return

    if channels.is_offline_channel(message.channel):
        # No bot shenanigans in the off channel
        return

    if (channels.is_cmd_line(message.channel.name)
        or channels.is_outbox(message.channel.name)
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
    await players.create_player(member)


# Commands related to handles
# These work in both cmd_line and outbox channels

@bot.command(name='handle', help='Show current handle, or switch to another handle. To switch, new handle must be free (then it will be created) or controlled by you. Your handle is shown to other users in most other channels.')
async def switch_handle_command(ctx, new_handle : str=None, burner=False):
    response = await handles.process_handle_command(ctx, new_handle, burner)
    if channels.is_cmd_line(ctx.channel.name):
        await ctx.send(response)
    elif channels.is_chat_hub(ctx.channel.name):
        # TODO: perform the action, but do not send the report
        await ctx.send(response)

@bot.command(name='burner', help='Create a new burner handle, or switch to one that you already that you have not burned yet.')
async def create_burner_command(ctx, new_id : str=None):
    await switch_handle_command(ctx, new_id, True)


@bot.command(name='burn', help='Destroy a burner account forever.')
async def burn_command(ctx, burner_id : str=None):
    response = await process_burn_command(ctx, burner_id)
    await ctx.send(response)


# Commands related to money
# These only work in cmd_line channels

@bot.command(name='create_money', help='Use \".create_money <handle> <amount>\" to create new money (will be admin-only during the game)')
@commands.has_role('gm')
async def create_money_command(ctx, handle : str=None, amount : int=0):
    if not channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return

    if handle == None:
        response = 'Error: no handle specified.'
    else:
        handle = handle.lower()
        if amount <= 0:
            response = 'Error: cannot create less than ¥ 1.'
        elif handles.handle_exists(handle):
            await finances.add_funds(ctx.guild, handle, amount)
            response = 'Added ' + str(amount) + ' to the balance of ' + handle
        else:
            response = 'Error: handle \"' + handle + '\" does not exist.'
    await ctx.send(response)

@bot.command(name='set_money', help='Use \".set_money <handle> <amount>\" to set the balance of an account (will be admin-only during the game)')
@commands.has_role('gm')
async def set_money_command(ctx, handle : str=None, amount : int=-1):
    if not channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return

    if handle == None:
        response = 'Error: no handle specified.'
    else:
        handle = handle.lower()
        if amount < 0:
            response = 'Error: you must set a new balance.'
        elif handles.handle_exists(handle):
            await finances.overwrite_balance(ctx.guild, handle, amount)
            response = 'Set the balance of ' + handle + ' to ' + str(amount)
        else:
            response = 'Error: handle \"' + handle + '\" does not exist.'
    await ctx.send(response)

@bot.command(name='pay', help='Pay money (¥) to the owner of another handle')
async def pay_money_command(ctx, handle_recip : str=None, amount : int=0):
    if not channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return

    if handle_recip == None:
        response = 'Error: no recipient specified. Use \".pay <recipient> <amount>\", e.g. \".pay Shadow_Weaver 500\".'
    else:
        handle_recip = handle_recip.lower()
        if amount <= 0:
            response = 'Error: cannot transfer less than ¥ 1. Use \".pay <recipient> <amount>\", e.g. \".pay Shadow_Weaver 500\".'
        else:
            player_id = players.get_player_id(str(ctx.message.author.id))
            transaction : custom_types.Transaction = await finances.try_to_pay(ctx.guild, player_id, handle_recip, amount)
            response = transaction.report
    await ctx.send(response)

@bot.command(name='balance', help='Show current balance (amount of money available) on all available handles.')
async def show_balance_command(ctx):
    if not channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return

    player_id = players.get_player_id(str(ctx.message.author.id))
    response = finances.get_all_handles_balance_report(player_id)
    await ctx.send(response)

@bot.command(name='collect', help='Collect all your funds from all handles to the current handle\'s account')
async def collect_command(ctx):
    if not channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return

    player_id = players.get_player_id(str(ctx.message.author.id))
    response = 'Collecting all funds to the account of the current handle...'
    await asyncio.create_task(ctx.send(response))
    await asyncio.create_task(finances.collect_all_funds(ctx.guild, player_id))
    #await show_balance_command(ctx)


# Commands for passing messages / email

@bot.command(name='message', help='Send message to another handle. Only works in your \"outbox\" channel.')
async def message_command(ctx, handle : str = None, content : str = None):
    if not channels.is_outbox(ctx.channel.name):
        response = 'Error: you cannot send messages from here. Go to your #outbox channel and use .message there.'
        await ctx.send(response)
        return
    if handle == None or content == None:
        response = 'Error: use \'.message <recipient> \"message\"\', e.g. \'.message Shadow_Weaver \"Oi chummer!\"\'.'
        await ctx.send(response)
        return

    handle = handle.lower()
    await posting.process_email(ctx, handle, content)

# Admin-only commands for testing etc.

@bot.command(name='fake_join', help='Admin-only function to test run the new member mechanics')
@commands.has_role('gm')
async def fake_join_command(ctx, user_id):
    member_to_fake_join = await ctx.guild.fetch_member(user_id)
    if member_to_fake_join == None:
        await ctx.send(f'Failed: member with user_id {user_id} not found.')
    else:
        await on_member_join(member_to_fake_join)

@bot.command(name='fake_join_name', help='Admin-only function to test run the new member mechanics')
@commands.has_role('gm')
async def fake_join_command(ctx, name : str):
    members = await ctx.guild.fetch_members(limit=100).flatten()
    member_to_fake_join = discord.utils.find(lambda m: m.name == name, members)
    if member_to_fake_join == None:
        await ctx.send(f'Failed: member with name {name} not found.')
    else:
        await on_member_join(member_to_fake_join)

@bot.command(name='fake_join_nick', help='Admin-only function to test run the new member mechanics')
@commands.has_role('gm')
async def fake_join_command(ctx, nick : str):
    members = await ctx.guild.fetch_members(limit=100).flatten()
    member_to_fake_join = discord.utils.find(lambda m: m.nick == nick, members)
    if member_to_fake_join == None:
        await ctx.send(f'Failed: member with nick {nick} not found.')
    else:
        await on_member_join(member_to_fake_join)

@bot.command(name='clear_all_players', help='Admin-only: de-initialise all players.')
@commands.has_role('gm')
async def clear_all_players_command(ctx):
    await players.init(bot, guild, clear_all=True)
    await ctx.send('Done.')

@bot.command(name='init_all_players', help='Admin-only: initialise all current members of the server as players.')
@commands.has_role('gm')
async def init_all_players_command(ctx):
    await players.initialise_all_users(guild)
    await ctx.send('Done.')

@bot.command(name='ping', help='Admin-only function to test user-player-channel mappings')
@commands.has_role('gm')
async def ping_command(ctx, handle : str):
    channel = players.get_cmd_line_channel_for_handle(ctx.guild, handle)
    if channel != None:
        await channel.send(f'Testing ping for {handle}')
    else:
        ctx.send(f'Error: could not find the command line channel for {handle}')

# Chats

# TODO: add handling for using .chat and .close_chat without argument
@bot.command(name='chat', help='Open a chat session with another user.')
async def chat_command(ctx, handle : str):
    handle = handle.lower()
    if not channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return
    await chats.create_chat_from_command(ctx, handle)

@bot.command(name='chat_other', help='Admin-only: open a chat session for someone else.')
async def chat_other_command(ctx,  my_handle : str, other_handle : str):
    my_handle = my_handle.lower()
    other_handle = other_handle.lower()
    if not channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return
    report = await chats.create_2party_chat(my_handle, other_handle)
    if report != None:
        await ctx.send(report)

@bot.command(name='close_chat', help='Close a chat session from your end.')
async def close_chat_command(ctx, handle : str):
    handle = handle.lower()
    if not channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return
    await chats.close_chat_session_from_command(ctx, handle)


@bot.command(name='close_chat_other', help='Admin-only: close a chat session for someone else.')
@commands.has_role('gm')
async def close_chat_other_command(ctx, my_handle : str, other_handle : str):
    my_handle = my_handle.lower()
    other_handle = other_handle.lower()
    if not channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return
    report = await chats.close_2party_chat_session(my_handle, other_handle)
    if report != None:
        await ctx.send(report)

@bot.command(name='clear_all_chats', help='Admin-only: delete all chats and chat channels for all users.')
@commands.has_role('gm')
async def clear_all_chats_command(ctx):
    await chats.init(bot, clear_all=True)
    await ctx.send('Done.')


#@bot.command(name='read_chat', help='Admin-only function to test chats')
#@commands.has_role('gm')
#async def read_chat_command(ctx):
#    await chats.read_chat()

bot.run(TOKEN)
