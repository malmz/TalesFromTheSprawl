import discord
import asyncio
from configobj import ConfigObj
import simplejson

import players
import handles
import channels
import server
import posting

chats_dir = 'chats'
chats = ConfigObj(f'{chats_dir}/chats.conf')

channel_id_index = '___channel_id'
handle_index = '___handle'
player_id_index = '___player_id'
chat_name_index = '___chat_name'
chat_channel_data_index = '___chat_channel_data'
chat_content_index = '___chat_content'
chat_connection_index = '___chat_connection'


### Classes, init and basic utilities

class ChatConnection(object):
	def __init__(self, chat_name : str, player_id : str, handle : str, channel_id : str=None):
		self.chat_name = chat_name
		self.player_id = player_id
		self.handle = handle
		# Set to None when the channel is temporarily closed
		self.channel_id = channel_id
		#TODO: message_id pointing to a message in player's cmd_line or similar, with open/close buttons

	@staticmethod
	def from_string(string : str):
		obj = ChatConnection(None, None, None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)


# TODO: rename ChannelToChatMapping
class ChatChannelData(object):
	def __init__(self, channel_id : str, chat_name : str, player_id : str, handle : str):
		self.channel_id = channel_id
		self.chat_name = chat_name
		self.player_id = player_id
		self.handle = handle

	@staticmethod
	def from_string(string : str):
		obj = ChatChannelData(None, None, None, None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)

async def init(bot, reset_all : bool):
	if reset_all:
		await channels.delete_all_chats(bot)
	if not chat_channel_data_index in chats or reset_all:
		chats[chat_channel_data_index] = {}
	chats.write()

def read_chat_channel_data(channel_id : str):
	string = chats[chat_channel_data_index][channel_id]
	chat_channel_data : ChatChannelData = ChatChannelData.from_string(string)
	return chat_channel_data

def store_chat_channel_data(channel_id : str, chat_channel_data : ChatChannelData):
	chats[chat_channel_data_index][channel_id] = chat_channel_data.to_string()
	chats.write()

def clear_chat_channel_data(channel_id):
	del chats[chat_channel_data_index][channel_id]
	chats.write()

def read_chat_connection(chat_state, player_id : str):
	string = chat_state[chat_connection_index][player_id]
	chat_connection : ChatConnection = ChatConnection.from_string(string)
	return chat_connection

def store_chat_connection(chat_state, player_id : str, chat_connection : ChatConnection):
	chat_state[chat_connection_index][player_id] = chat_connection.to_string()
	chat_state.write()

def get_chat_name(handle1 : str, handle2 : str):
	handles_ordered = sorted([handle1, handle2])
	return f'{handles_ordered[0]}_{handles_ordered[1]}'

def get_chat_state(chat_name : str):
	chat_file_name = f'{chat_name}.conf'
	return ConfigObj(f'{chats_dir}/{chat_file_name}')

### Creating a new chat

async def create_chat(ctx, recip_handle):
	creator_user_id = str(ctx.message.author.id)
	creator_player_id = players.get_player_id(creator_user_id)
	creator_handle = handles.get_handle(creator_player_id)

	if creator_handle == recip_handle:
		await ctx.send(f'Error: {recip_handle} is your current handle – cannot open chat with yourself.')
		return

	recip_status : handles.HandleStatus = handles.get_handle_status(recip_handle)
	if not recip_status.exists:
		await ctx.send(f'Error: could not open chat with {recip_handle}; recipient does not exist.')
		return
	recip_player_id = recip_status.player_id

	# data common to both participants:
	chat_name = get_chat_name(creator_handle, recip_handle)
	# TODO: check whether chat already exists
	channels.init_chat_channel(chat_name)

	# Chat-specific config: will hold all history, but also players' active handles and channels
	# TODO: refactor into init_chat_state
	chat_state = get_chat_state(chat_name)
	chat_state[chat_connection_index] = {}
	chat_state[chat_content_index] = {}
	chat_state.write()

	# data that is needed separately for each participant:
	creator_clickable_channel_ref = (
		await create_chat_for_participant(
			ctx.guild,
			chat_state,
			chat_name,
			creator_handle,
			creator_player_id,
			recip_handle
		)
	)
	recip_clickable_channel_ref = (
		await create_chat_for_participant(
			ctx.guild,
			chat_state,
			chat_name,
			recip_handle,
			recip_player_id,
			creator_handle
		)
	)

	if creator_player_id == recip_player_id:
		report = (f'Opened chat between {creator_handle} and {recip_handle}. '
			+ 'Note that both handles are controlled by you, so you will be chatting with yourself. '
			+ f'Channels are available at {creator_clickable_channel_ref} and {recip_clickable_channel_ref}.'
		)
	else:
		report = f'Opened chat between {creator_handle} and {recip_handle}: {creator_clickable_channel_ref} (other channel is at {recip_clickable_channel_ref})'
	await ctx.send(report)

async def create_chat_for_participant(guild, chat_state, chat_name : str, my_handle : str, my_player_id : str, partner_handle : str):
	# TODO: for creator, this might mean closing another chat (but check for that before creating?)
	# TODO: for recip, we must check if chat can be opened and possibly close it
	# TODO: when reopening an existing chat (down the line when we track storing everything),
	# we should FIRST post all the message history, and THEN add the role to give visibility
	channel_name = f'{my_handle}_to_{partner_handle}'
	channel = await channels.create_chat_session_channel(guild, my_player_id, channel_name)
	channel_id = str(channel.id)
	clickable_channel_ref = channels.clickable_channel_ref(channel)

	# channel ID -> chat mapping
	chat_channel_data = ChatChannelData(channel_id, chat_name, my_player_id, my_handle)
	store_chat_channel_data(channel_id, chat_channel_data)	# chat name -> full chat log file name mapping
	chats.write()
	
	# chat -> channel ID mapping
	chat_connection = ChatConnection(chat_name, my_player_id, my_handle, channel_id)
	store_chat_connection(chat_state, my_player_id, chat_connection)
	chat_state.write()

	return clickable_channel_ref


### Close and reopen chat


async def close_chat_session(my_handle : str, partner_handle : str):
	# probably not needed as special case
	#if creator_handle == partner_handle:
	#	await ctx.send(f'Error: {partner_handle} is your current handle – there is no chat.')
	#	return
	my_status : handles.HandleStatus = handles.get_handle_status(my_handle)
	if not my_status.exists:
		raise RuntimeError(f'Tried to close chat but initiator handle {my_handle} does not exist.')

	partner_status : handles.HandleStatus = handles.get_handle_status(partner_handle)
	if not partner_status.exists:
		return f'Error: no chat with {partner_handle} found; recipient does not exist. Check the spelling.'
	partner_player_id = partner_status.player_id

	chat_name = get_chat_name(my_handle, partner_handle)
	chat_state = get_chat_state(chat_name)

	# update chat -> channel ID mapping
	chat_connection : ChatConnection = read_chat_connection(chat_state, my_status.player_id)
	channel_id_to_close = chat_connection.channel_id
	chat_connection.channel_id = None
	store_chat_connection(chat_state, my_status.player_id, chat_connection)

	# Close the session, i.e. delete the player's discord channel
	await channels.delete_discord_channel(channel_id_to_close)

	# Remove channel ID -> chat mapping
	clear_chat_channel_data(channel_id_to_close)

	return f'Closed chat session with {partner_handle}. To re-open, use \".chat {partner_handle}\".'
	



async def close_chat_session_from_ctx(ctx, partner_handle : str):
	creator_user_id = str(ctx.message.author.id)
	creator_player_id = players.get_player_id(creator_user_id)
	creator_handle = handles.get_handle(creator_player_id)
	report = await close_chat_session(creator_handle, partner_handle)
	if report != None:
		await ctx.send(report)



### Messages in chat

async def find_chat_channel_and_post(message, chat_connection : ChatConnection, poster_id : str):
	guild = server.get_guild()
	discord_channel = guild.get_channel(int(chat_connection.channel_id))
	if discord_channel == None:
		raise RuntimeError(f'Could not find channel with ID {chat_connection.channel_id}')
	else:
		await posting.repost_message_to_channel(discord_channel, message, poster_id)

def create_reposting_tasks(chat_name : str, message, poster_id : str):
	chat_state = get_chat_state(chat_name)
	for player_id in chat_state[chat_connection_index]:
		# TODO: if connection is closed, don't try to send to its channel
		chat_connection : ChatConnection = read_chat_connection(chat_state, player_id)
		if chat_connection.channel_id != None:
			yield asyncio.create_task(find_chat_channel_and_post(message, chat_connection, poster_id))

async def process_message(message):
	task1 = asyncio.create_task(message.delete())

	sender_channel = message.channel
	chat_channel_data : ChatChannelData = read_chat_channel_data(str(sender_channel.id))
	handle = chat_channel_data.handle
	chat_name = chat_channel_data.chat_name

	full_post = channels.record_new_post(chat_channel_data.chat_name, handle, message.created_at)
	poster_id = handle if full_post else None
	tasks = create_reposting_tasks(chat_name, message, poster_id)
	await asyncio.gather(task1, *tasks)

