# bot.py
import os
import random
import discord

from configobj import ConfigObj

from discord.ext import commands
from dotenv import load_dotenv
from collections import namedtuple

# Custom imports
import handles
import channels
import posting


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='.')

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    channels.init_channels()
    handles.init_stats()
    print('Initialization complete.')


# General message processing (reposting for anonymity/pseudonymity)

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
        await posting.process_message(message, True)
        return

    # All other channels: repost message using user's current handle
    await posting.process_message(message)


# Commands related to handles

@bot.command(name='handle', help='Switch to another handle for #open_channel and other channels. Handle must be free; once created, no-one else can use it.')
async def switch_handle_command(ctx, new_handle : str=None, burner = False):
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


# Commands related to money

@bot.command(name='create_money', help='[OFFLINE]')
@commands.has_role('admin')
async def create_money_command(ctx, handle : str=None, amount : int=0):
    if handle == None:
        response = 'Error, no handle specified.'
    elif handles.handle_exists(handle):
        handles.add_funds(handle, amount)
        response = 'Added ' + str(amount) + ' to the balance of ' + handle
    else:
        response = 'Error, handle \"' + handle + '\" does not exist.'
    await ctx.send(response)

@bot.command(name='pay', help='Pay money (nuyen) to the owner of another handle')
async def pay_money_command(ctx, handle_recip : str=None, amount : int=0):
    if handle_recip == None:
        response = 'Error: no recipient specified. Use \".pay <recipient> <amount>\", e.g. \".pay Shadow_Weaver 500\".'
    elif amount == 0:
        response = 'Error: cannot transfer ¥ 0. Use \".pay <recipient> <amount>\", e.g. \".pay Shadow_Weaver 500\".'
    else:
        user_id = str(ctx.message.author.id)
        response = handles.try_to_pay(user_id, handle_recip, amount)
    await ctx.send(response)

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