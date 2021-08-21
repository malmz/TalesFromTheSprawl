#module actors.py

### This module collects everything that is common to actors and shops.

import channels
import handles
import reactions
import finances
import common
import server
import shops

from custom_types import Transaction, Actor, TransTypes
from common import emoji_cancel

import discord
import asyncio
from configobj import ConfigObj
import re

actors_conf_dir = 'actors'
actors = ConfigObj('actors.conf')
actors_input = ConfigObj('actors_input.conf')


async def init(guild, clear_all=False):
	if clear_all:
		for actor_id in actors:
			await clear_actor(guild, actor_id)
		await channels.delete_all_personal_channels()
		await handles.clear_all_handles()
	else:
		for actor in get_all_actors():
			await handles.init_handles_for_actor(actor.actor_id, overwrite=False)
			# TODO: re-map all personal channels?
	await delete_all_actor_roles(guild, spare_used=(not clear_all))

async def clear_actor(guild, actor_id : str):
	if actor_exists(actor_id):
		# TODO: clear out/archive chat participants from all chats? Not required unless we expect to create and destroy actors during game
		actor = read_actor(actor_id)
		del actors[actor_id]
		actors.write()
		clear_trans_memory(actor_id)
		await channels.delete_all_personal_channels(channel_suffix=actor.actor_id)
		await handles.clear_all_handles_for_actor(actor_id)
		shops.delete_delivery_ids_for_actor(actor_id)
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



recent_transactions_suffix = '_recent_trans.conf'

def get_trans_mem(actor_id : str):
	trans_mem_file_name = f'{actor_id}{recent_transactions_suffix}'
	return ConfigObj(f'{actors_conf_dir}/{trans_mem_file_name}')

def get_all_recent_trans(actor_id : str):
	if actor_exists(actor_id):
		trans_mem = get_trans_mem(actor_id)
		for msg_id in trans_mem:
			yield read_transaction_from_memory(trans_mem, msg_id)

def store_transaction(actor_id : str, msg_id : str, transaction : Transaction):
	if actor_exists(actor_id):
		trans_mem = get_trans_mem(actor_id)
		trans_mem[msg_id] = transaction.to_string()
		trans_mem.write()

def delete_transaction(actor_id : str, msg_id : str):
	if actor_exists(actor_id):
		trans_mem = get_trans_mem(actor_id)
		if msg_id in trans_mem:
			del trans_mem[msg_id]
			trans_mem.write()

def read_transaction(actor_id : str, msg_id : str):
	if actor_exists(actor_id):
		trans_mem = get_trans_mem(actor_id)
		return read_transaction_from_memory(trans_mem, product_name)

def read_transaction_from_memory(msg_id : str):
	if msg_id in trans_mem:
		return Transaction.from_string(trans_mem[msg_id])

def clear_trans_memory(actor_id : str):
	if actor_exists(actor_id):
		trans_mem = get_trans_mem(actor_id)
		for entry in trans_mem:
			del trans_mem[entry]
		trans_mem.write()





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
	init_handles = asyncio.create_task(handles.init_handles_for_actor(actor_id))
	await asyncio.gather(chat_hub_welcome, finance_welcome, init_handles)

	actor = Actor(
		actor_index=actor_index,
		actor_id=actor_id,
		finance_channel_id=finances_channel.id,
		finance_stmt_msg_id=0,
		chat_channel_id=chat_hub_channel.id)
	store_actor(actor)
	clear_trans_memory(actor_id)
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

async def refresh_financial_statement(actor_id : str):
	actor = read_actor(actor_id)
	if actor is None:
		raise RuntimeError(f'Trying to write financial record but could not find which actor it belongs to.')
	channel = channels.get_discord_channel(actor.finance_channel_id)
	await update_financial_statement(channel, actor)

async def write_financial_record(transaction : Transaction, payer_record : str=None, recip_record : str=None):
	def send_record_task(actor_id : str, record : str):
		return asyncio.create_task(send_financial_record_for_actor(actor_id, record, transaction.last_in_sequence))

	task_list = (
		send_record_task(a, r)
		for (a, r)
		in [(transaction.payer_actor, payer_record), (transaction.recip_actor, recip_record)]
	)
	[payer_message, sender_message] = await asyncio.gather(*task_list)
	print(f'{payer_message}, {sender_message}')

	if transaction.cause == TransTypes.ShopOrder:
		if payer_message is not None:
			await payer_message.add_reaction(emoji_cancel)
			msg_id = str(payer_message.id)
			transaction.payer_msg_id = msg_id
			store_transaction(transaction.payer_actor, msg_id, transaction)
		if sender_message is not None:
			await sender_message.add_reaction(emoji_cancel)
			msg_id = str(sender_message.id)
			transaction.recip_msg_id = msg_id
			store_transaction(transaction.recip_actor, msg_id, transaction)
	print(f'Transaction at the end of write_financial_record: {transaction.to_string()}')

async def send_financial_record_for_actor(actor_id : str, record : str, last_in_sequence):
	print(f'{actor_id}, {record}')
	if record is not None:
		actor = read_actor(actor_id)
		if actor is None:
			raise RuntimeError(f'Trying to write financial record but could not find which actor it belongs to.')
		channel = channels.get_discord_channel(actor.finance_channel_id)
		message = await channel.send(record)
		if last_in_sequence:
			await update_financial_statement(channel, actor)
		return message

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

