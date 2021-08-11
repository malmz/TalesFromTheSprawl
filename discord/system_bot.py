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
import common_channels
import posting
import reactions
import players
import finances


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
    common_channels.init_channels(bot)
    #handles.init() #TODO: ensure that every user has a handle?
    finances.init_finances()
    players.init(bot, guild)
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

    if common_channels.is_offline_channel(message.channel):
        # No bot shenanigans in the off channel
        return

    if common_channels.is_cmd_line(message.channel.name) or common_channels.is_outbox(message.channel.name):
        await bot.process_commands(message)
        return        

    if common_channels.is_anonymous_channel(message.channel):
        await posting.process_message(message, True)
        return

    if common_channels.is_pseudonymous_channel(message.channel):
        await posting.process_message(message)



# General reaction handling

@bot.event
async def on_raw_reaction_add(payload):
    channel = await bot.fetch_channel(payload.channel_id)
    if payload.user_id == bot.user.id:
        # Don't act on bot's own reactions to avoid loops
        return

    if common_channels.is_offline_channel(channel):
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
    user_id = str(ctx.message.author.id)
    if new_handle == None:
        response = handles.try_switch_to_none_handle(user_id)
    else:
        handle_status : HandleStatus = handles.get_handle_status(new_handle)
        if (handle_status.exists and handle_status.user_id == user_id):
            response = handles.switch_to_own_existing_handle(user_id, new_handle, handle_status, burner)
        elif (handle_status.exists):
            response = 'Error: the handle ' + new_handle + ' is currently registered by someone else'
        else:
            response = handles.create_handle_and_switch(user_id, new_handle, burner)
    await ctx.send(response)

@bot.command(name='burner', help='Create a new burner handle, or switch to one that you already that you have not burned yet.')
async def create_burner_command(ctx, new_id : str=None):
    await switch_handle_command(ctx, new_id, True)


@bot.command(name='burn', help='Destroy a burner account forever.')
async def burn_command(ctx, burner_id : str=None):
    if burner_id == None:
        response = 'Error: No burner handle specified. Use \".burn <handle>\"'
    else:
        user_id = str(ctx.message.author.id)
        handle_status : handles.HandleStatus = handles.get_handle_status(burner_id)
        if (not handle_status.exists):
            response = 'Error: the handle ' + burner_id + ' does not exist'
        elif (handle_status.user_id != user_id):
            response = 'Error: you do not have access to ' + burner_id
        elif (handle_status.handle_type == 'regular'):
            response = 'Error: **' + burner_id + '** is not a burner handle, cannot be destroyed. To stop using it, simply switch to another handle.'
        elif (handle_status.handle_type == 'burner'):
            amount = handles.destroy_burner(user_id, burner_id)
            current_handle = handles.get_handle(user_id)
            response = 'Destroyed burner handle **' + burner_id + '**.\n'
            response = response + 'If you or someone else uses that name, it may be confusing but cannot be traced to the previous use.\n'
            if amount > 0:
                response = response + f'Your current handle is **{current_handle}**; the remaining ¥ {amount} from {burner_id} was transferred there.'
            else:
                response = response + 'Your current handle is **' + current_handle + '**.'
    await ctx.send(response)


# Commands related to money
# These only work in cmd_line channels

@bot.command(name='create_money', help='Use \".create_money <handle> <amount>\" to create new money (will be admin-only during the game)')
@commands.has_role('gm')
async def create_money_command(ctx, handle : str=None, amount : int=0):
    if not common_channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return

    if handle == None:
        response = 'Error: no handle specified.'
    elif amount <= 0:
        response = 'Error: cannot create less than ¥ 1.'
    elif handles.handle_exists(handle):
        finances.add_funds(handle, amount)
        response = 'Added ' + str(amount) + ' to the balance of ' + handle
    else:
        response = 'Error: handle \"' + handle + '\" does not exist.'
    await ctx.send(response)

@bot.command(name='set_money', help='Use \".set_money <handle> <amount>\" to set the balance of an account (will be admin-only during the game)')
@commands.has_role('gm')
async def set_money_command(ctx, handle : str=None, amount : int=-1):
    if not common_channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return

    if handle == None:
        response = 'Error: no handle specified.'
    elif amount < 0:
        response = 'Error: you must set a new balance.'
    elif handles.handle_exists(handle):
        finances.set_current_balance(handle, amount)
        response = 'Set the balance of ' + handle + ' to ' + str(amount)
    else:
        response = 'Error: handle \"' + handle + '\" does not exist.'
    await ctx.send(response)

@bot.command(name='pay', help='Pay money (¥) to the owner of another handle')
async def pay_money_command(ctx, handle_recip : str=None, amount : int=0):
    if not common_channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return

    if handle_recip == None:
        response = 'Error: no recipient specified. Use \".pay <recipient> <amount>\", e.g. \".pay Shadow_Weaver 500\".'
    elif amount <= 0:
        response = 'Error: cannot transfer less than ¥ 1. Use \".pay <recipient> <amount>\", e.g. \".pay Shadow_Weaver 500\".'
    else:
        user_id = str(ctx.message.author.id)
        response = await finances.try_to_pay(ctx.guild, user_id, handle_recip, amount)
    await ctx.send(response)

@bot.command(name='balance', help='Show current balance (amount of money available) on all available handles.')
async def show_balance_command(ctx):
    if not common_channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return

    user_id = str(ctx.message.author.id)
    report = finances.get_all_handles_balance_report(user_id)
    response = 'Current balance for all your accounts:\n' + report
    await ctx.send(response)

@bot.command(name='collect', help='Collect all your funds from all handles to the current handle\'s account')
async def collect_command(ctx):
    if not common_channels.is_cmd_line(ctx.channel.name):
        await swallow(ctx.message);
        return

    user_id = str(ctx.message.author.id)
    response = 'Collecting all funds to the account of the current handle...'
    await ctx.send(response)
    finances.collect_all_funds(user_id)
    await show_balance_command(ctx)



# Commands for passing messages / email

@bot.command(name='message', help='Send message to another handle. Only works in your \"outbox\" channel.')
async def message_command(ctx, handle : str = None, content : str = None):
    if not common_channels.is_outbox(ctx.channel.name):
        response = 'Error: you cannot send messages from here. Go to your #outbox channel and use .message there.'
        await ctx.send(response)
        return
    if handle == None or content == None:
        response = 'Error: use \'.message <recipient> \"message\"\', e.g. \'.message Shadow_Weaver \"Oi chummer!\"\'.'
        await ctx.send(response)
        return

    await posting.process_email(ctx, handle, content)

# Admin-only commands for testing etc.

@bot.command(name='fake_join', help='Admin-only function to test run the new member mechanics')
@commands.has_role('gm')
async def fake_join_command(ctx, user_id):
    member_to_fake_join = await ctx.guild.fetch_member(user_id)
    await on_member_join(member_to_fake_join)

@bot.command(name='fake_join_name', help='Admin-only function to test run the new member mechanics')
@commands.has_role('gm')
async def fake_join_command(ctx, nick : str):
    members = await ctx.guild.fetch_members(limit=100).flatten()
    print(f'{members}')
    member_to_fake_join = discord.utils.find(lambda m: m.name == nick, members)
    await on_member_join(member_to_fake_join)


@bot.command(name='ping', help='Admin-only function to test user-player-channel mappings')
@commands.has_role('gm')
async def ping_command(ctx, handle : str):
    channel = players.get_inbox_channel_for_handle(ctx.guild, handle)
    if channel != None:
        await channel.send(f'Testing ping for {handle}')
    else:
        print(f'Error: could not find the command line channel for {handle}')

bot.run(TOKEN)
