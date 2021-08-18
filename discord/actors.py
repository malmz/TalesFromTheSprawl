#module actors.py

### This module collects everything that is common to actors and shops.

import channels
import handles
import reactions
import finances
import common
import server

from custom_types import Transaction, Actor

import discord
import asyncio
from configobj import ConfigObj
import re


actors = ConfigObj('actors.conf')
actors_input = ConfigObj('actors_input.conf')


# TODO: loop through all users, find their actor_ids and re-map personal channels if not available
async def init(bot, guild, clear_all=False):
	if clear_all:
		for actor_id in actors:
			del actors[actor_id]
		await channels.delete_all_personal_channels(bot)
		await handles.clear_all_handles()
	await delete_all_actor_roles(guild, spare_used=(not clear_all))
	actors.write()

async def clear_actor(bot, guild, actor_id : str):
	if actor_exists(actor_id):
		actor = read_actor(actor_id)
		del actors[actor_id]
		actors.write()
		await channels.delete_all_personal_channels(bot, actor.actor_id)
		await handles.clear_all_handles_for_actor(actor_id)
		await delete_all_actor_roles(guild, spare_used=True)
		return 'Done'
	else:
		return f'Could not find actor {actor_id}'


async def delete_all_actor_roles(guild, spare_used : bool):
	task_list = (asyncio.create_task(delete_if_actor_role(r, spare_used)) for r in guild.roles)
	await asyncio.gather(*task_list)

async def delete_if_actor_role(role, spare_used : bool):
	if await is_actor_role(role.name):
		if not spare_used or len(role.members) == 0:
			print(f'Deleting unused role with name {role.name}')
			await role.delete()

async def is_actor_role(name :str):
	return common.is_player_role(name) or common.is_shop_role(name)

def get_actor_role(guild, actor_id : str):
	actor = read_actor(actor_id)
	if actor is not None:
		return discord.utils.find(lambda role: role.name == actor.actor_index, guild.roles)


def get_all_actors():
	for actor_id in actors:
		yield read_actor(actor_id)

def actor_exists(actor_id : str):
	return actor_id in actors

def store_actor(actor : Actor):
	actors[actor.actor_id] = actor.to_string()
	actors.write()

def read_actor(actor_id : str):
	if actor_id in actors:
		return Actor.from_string(actors[actor_id])


async def give_actor_access(guild, channel, actor_id : str):
	role = get_actor_role(guild, actor_id)
	await server.give_role_access(channel, role)

async def create_new_actor(guild, actor_index : str, actor_id : str):
	# Create role for this actor:
	role = await guild.create_role(name=actor_index)

	# Create personal channels for user:
	chat_hub_creation = asyncio.create_task(channels.create_personal_channel(
		guild,
		role,
		channels.get_chat_hub_name(actor_id)
	))

	finances_creation = asyncio.create_task(channels.create_personal_channel(
		guild,
		role,
		channels.get_finance_name(actor_id),
		read_only=True
	))

	[chat_hub_channel, finances_channel] = (
		await asyncio.gather(chat_hub_creation, finances_creation)
	)

	# Send welcome messages to the channels (no-one has the role to see it yet)
	chat_hub_welcome = asyncio.create_task(send_startup_message_chat_hub(chat_hub_channel, actor_id))
	finance_welcome = asyncio.create_task(send_startup_message_finance(finances_channel, actor_id))
	await asyncio.gather(chat_hub_welcome, finance_welcome)

	actor = Actor(
		actor_index=actor_index,
		actor_id=actor_id,
		finance_channel_id=finances_channel.id,
		finance_stmt_msg_id=0,
		chat_channel_id=chat_hub_channel.id)
	store_actor(actor)

	handles.init_handles_for_actor(actor_id)

	return actor

async def send_startup_message_finance(channel, actor_id : str):
	content = f'This is the financial record for {actor_id}.\n'
	content = content + 'A record of every transaction—involving any handle you control—will appear here. You cannot send anything in this channel.'
	await channel.send(content)

async def send_startup_message_chat_hub(channel, actor_id : str):
	content = f'This is the chat hub for {actor_id}.'
	content += ' All your chat connections will be visible here. If you close a chat, you can find it here to re-open it.\n '
	content += 'You can start new chats by typing \".chat <handle>\" or [NOT IMPLEMENTED YET] \".room <room_name>\".'
	await channel.send(content)

async def get_financial_statement(channel, actor : Actor):
	if actor.finance_stmt_msg_id > 0:
		try:
			return await channel.fetch_message(actor.finance_stmt_msg_id)
		except discord.errors.NotFound:
			pass

async def update_financial_statement(channel, actor : Actor):
	message = await get_financial_statement(channel, actor)
	if message is not None:
		await message.delete()

	report = finances.get_all_handles_balance_report(actor.actor_id)
	content = '========================\n' + report

	new_message = await channel.send(content)
	actor.finance_stmt_msg_id = new_message.id
	store_actor(actor)


async def write_financial_record(actor_id : str, content : str, last_in_sequence : bool):
	actor = read_actor(actor_id)
	if actor is None:
		raise RuntimeError(f'Trying to write financial record but could not find which actor it belongs to.')
	channel = channels.get_discord_channel(actor.finance_channel_id)
	if content is not None:
		await channel.send(content)
	if last_in_sequence:
		await update_financial_statement(channel, actor)

def get_actor_for_handle(handle_id : str):
	handle : handles.Handle = handles.get_handle(handle_id)
	if handle.actor_id is not None:
		return read_actor(handle.actor_id)

def get_finance_channel_for_handle(handle : str):
	actor : Actor = get_actor_for_handle(handle)
	if actor is not None:
		return channels.get_discord_channel(actor.finance_channel_id)

def get_finance_channel(actor_id : str):
	actor : Actor = read_actor(actor_id)
	if actor is not None:
		return channels.get_discord_channel(actor.finance_channel_id)


def get_chat_hub_channel_for_handle(handle : str):
	actor : Actor = get_actor_for_handle(handle)
	if actor is not None:
		return channels.get_discord_channel(actor.chat_channel_id)

def get_chat_hub_channel(actor_id : str):
	actor : Actor = read_actor(actor_id)
	if actor is not None:
		return channels.get_discord_channel(actor.chat_channel_id)

