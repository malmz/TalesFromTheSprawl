# bot.py
import os
import random
import discord
import handles
import channels

from configobj import ConfigObj

from discord.ext import commands
from dotenv import load_dotenv
from collections import namedtuple

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='.')

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    channels.init_channels()
    handles.init_stats()
    print('Initialization complete.')


async def repost_message(message, handle):
    if handle == None:
        post = message.content
    else:
        timestamp = message.created_at
        timestamp_str = '(' + str(timestamp.hour) + ':' + str(timestamp.minute) + ':' + str(timestamp.second) + ')'
        post = '**' + handle + '** ' + timestamp_str + ':\n' + message.content
    await message.channel.send(post)

async def process_message(message, anonymous=False):
    await message.delete()
    current_channel = str(message.channel.name)
    user_id = str(message.author.id)
    if anonymous:
        current_poster_id = user_id
        current_poster_display_name = 'Anonymous'
    else:
        handle = handles.get_handle(user_id)
        current_poster_id = handle
        current_poster_display_name = handle
    full_post = channels.new_post(current_channel, current_poster_id, message.created_at)
    if full_post:
        await repost_message(message, current_poster_display_name)
    else:
        await repost_message(message, None)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        # Never react to bot's own message to avoid loops
        return

    if message.channel.name == 'offline':
        # No bot shenanigans in the off channel
        return

    if message.channel.name == 'command_line':
        await bot.process_commands(message)
        return

    if message.channel.name == 'anon':
        await process_message(message, True)
        return

    # All other channels: repost message using user's current handle
    await process_message(message)

@bot.command(name='oi', help='Responds with a hearty OI CHUMMER!')
async def oi(ctx):
    response = 'OI CHUMMER!'
    await ctx.send(response)

def try_switch_to_none_handle(user_id : str):
    current_handle = handles.get_handle(user_id)
    handle_status : handles.HandleStatus = handles.get_handle_status(current_handle)
    if (handle_status.handle_type == 'burner'):
        response = 'Your current handle is **' + current_handle + '**. It\'s a burner handle – to destroy it, use \".burn ' + current_handle + '\". To switch handle, type \".handle <new_name>\" in #command_line.'
    else:
        response = 'Your current handle is **' + current_handle + '**. To switch handle, type \".handle <new_name>\" in #command_line.'
    return response

def switch_to_own_existing_handle(user_id : str, new_handle : str, handle_status : handles.HandleStatus, new_shall_be_burner):
    if (handle_status.handle_type == 'burner'):
        # We can switch to a burner handle using both .handle and .burner
        response = 'Switched to burner handle **' + new_handle + '**. Remember to burn it when done, using \".burn ' + new_handle + '\" in #command_line.'
        handles.switch_to_handle(user_id, new_handle)
    elif new_shall_be_burner:
        # We cannot switch to a non-burner using .burner
        response = 'Handle **' + new_handle + '** already exists but is not a burner handle. Use \".handle ' + new_handle + '\" to switch to it.'
    else:
        response = 'Switched to handle **' + new_handle + '**.'
        handles.switch_to_handle(user_id, new_handle)
    return response

def create_handle_and_switch(user_id : str, new_handle : str, new_shall_be_burner):
    if new_shall_be_burner:
        # TODO: note about possibly being hacked until destroyed?
        response = 'Switched to new burner handle **' + new_handle + '** (created now). To destroy it, use \".burn ' + new_handle + '\" in #command_line.'
        handles.create_burner(user_id, new_handle)
    else:
        response = 'Switched to new handle **' + new_handle + '** (created now).'
        handles.create_handle(user_id, new_handle)
    handles.switch_to_handle(user_id, new_handle)
    return response

@bot.command(name='handle', help='Switch to another handle for #open_channel and other channels. Handle must be free; once created, no-one else can use it.')
async def switch_handle_command(ctx, new_handle : str=None, burner = False):
    user_id = str(ctx.message.author.id)
    if new_handle == None:
        response = try_switch_to_none_handle(user_id)
    else:
        handle_status : HandleStatus = handles.get_handle_status(new_handle)
        if (handle_status.exists and handle_status.user_id == user_id):
            response = switch_to_own_existing_handle(user_id, new_handle, handle_status, burner)
        elif (handle_status.exists):
            response = 'Error: the handle ' + new_handle + ' is currently registered by someone else'
        else:
            response = create_handle_and_switch(user_id, new_handle, burner)
    await ctx.send(response)

@bot.command(name='burner', help='Create a burner account for #open_channel and other channels')
async def create_burner_command(ctx, new_id : str=None):
    await switch_handle_command(ctx, new_id, True)

@bot.command(name='burn', help='Destroy a burner account forever')
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
            handles.destroy_burner(user_id, burner_id)
            current_handle = handles.get_handle(user_id)
            response = 'Destroyed burner handle **' + burner_id + '**. If you or someone else uses that name, it may be confusing but cannot be traced to the previous use. Your current handle is **' + current_handle + '**.'
    await ctx.send(response)

@bot.command(name='create_money', help='[OFFLINE]')
@commands.has_role('admin')
async def create_money_command(ctx, handle : str=None, amount : int=0):
    if handle == None:
        response = 'Error, no handle specified.'
    else:
        handles.add_funds(handle, amount)
        response = 'Added ' + str(amount) + ' to the balance of ' + handle
    await ctx.send(response)


def try_to_pay(user_id : str, handle_recip : str, amount : int):
    current_handle = handles.get_handle(user_id)
    if current_handle == handle_recip:
        response = 'Error: cannot transfer funds from account ' + handle_recip + ' to itself.'
        return response
    recip_status : handles.HandleStatus = handles.get_handle_status(handle_recip)
    if not recip_status.exists:
        response = 'Error: recipient \"' + handle_recip + '\" does not exist. Check the spelling; lowercase/UPPERCASE matters.'
    else:
        success = handles.transfer_funds(current_handle, handle_recip, amount)
        if not success:
            avail = handles.get_current_balance(current_handle)
            response = 'Error: insufficient funds. Current balance is **' + str(avail) + '**.'
        elif recip_status.user_id == user_id:
            response = 'Successfully transferred **¥' + str(amount) + '** from ' + current_handle + ' to **' + handle_recip + '**. (Note: you control both accounts.)'
        else:
            response = 'Successfully transferred **¥' + str(amount) + '** from ' + current_handle + ' to **' + handle_recip + '**.'
    return response


@bot.command(name='pay', help='Pay money (nuyen) to the owner of another handle')
async def pay_money_command(ctx, handle_recip : str=None, amount : int=0):
    if handle_recip == None:
        response = 'Error: no recipient specified. Use \".pay <recipient> <amount>\", e.g. \".pay Shadow_Weaver 500\".'
    elif amount == 0:
        response = 'Error: cannot transfer ¥0. Use \".pay <recipient> <amount>\", e.g. \".pay Shadow_Weaver 500\".'
    else:
        user_id = str(ctx.message.author.id)
        response = try_to_pay(user_id, handle_recip, amount)
    await ctx.send(response)

#@bot.command(name='balance', help='Show current balance (amount of money available) on the current handle.')
#async def show_balance_command(ctx):
#    user_id = str(ctx.message.author.id)
#    current_handle = handles.get_handle(user_id)
#    avail = handles.get_current_balance(current_handle)
#    response = 'Current balance for ' + current_handle + ' is **¥' + str(avail) + '**.'
#    await ctx.send(response)

@bot.command(name='balance', help='Show current balance (amount of money available) on all available handles.')
async def show_balance_command(ctx):
    user_id = str(ctx.message.author.id)
    report = handles.get_all_handles_balance_report(user_id)
    response = 'Current balance for all your accounts:\n' + report
    await ctx.send(response)

@bot.command(name='collect', help='Collect all your funds from all handles to the current handle\'s account')
async def collect_command(ctx):
    user_id = str(ctx.message.author.id)
    response = 'Collecting all funds to the account of the current handle...'
    await ctx.send(response)
    handles.collect_all_funds(user_id)
    await show_balance_command(ctx)

bot.run(TOKEN)