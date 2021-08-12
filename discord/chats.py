import asyncio
from configobj import ConfigObj
import simplejson

import players
import handles
import channels
import server

chats_dir = 'chats'
chats = ConfigObj(f'{chats_dir}/chats.conf')

file_name_index = '___file'
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
		obj = ChatConnection()
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)


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
	if not file_name_index in chats or reset_all:
		chats[file_name_index] = {}
	chats.write()


def get_chat_data_from_channel_id(channel_id : str):
	string = chats[chat_channel_data_index][channel_id]
	chat_channel_data : ChatChannelData = ChatChannelData.from_string(string)
	return chat_channel_data



### Creating a new chat

async def create_chat(ctx, recip_handle):
	creator_user_id = str(ctx.message.author.id)
	creator_player_id = players.get_player_id(creator_user_id)
	creator_handle = handles.get_handle(creator_player_id)

	recip_status : handles.HandleStatus = handles.get_handle_status(recip_handle)
	if not recip_status.exists:
		await ctx.send(f'Error: could not open chat with {recip_handle}; recipient does not exist.')
	recip_player_id = recip_status.player_id

	handles_ordered = sorted([creator_handle, recip_handle])

	# data common to both participants:
	# TODO: check whether chat already exists
	chat_name = f'{handles_ordered[0]}_{handles_ordered[1]}'
	chat_file_name = f'{chat_name}.conf'
	chats[file_name_index][chat_name] = chat_file_name
	chats.write()

	# Chat-specific config: will hold all history, but also players' active handles and channels
	chat_state = ConfigObj(f'{chats_dir}/{chat_file_name}')
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

	report = f'Opened chat between {creator_handle} and {recip_handle}: {creator_clickable_channel_ref} (other channel is at {recip_clickable_channel_ref})'
	await ctx.send(report)

async def create_chat_for_participant(guild, chat_state, chat_name : str, my_handle : str, my_player_id : str, partner_handle : str):
	# TODO: for creator, this might mean closing another chat (but check for that before creating?)
	# TODO: for recip, we must check if chat can be opened and possibly close it
	channel_name = f'{my_handle}_to_{partner_handle}'
	channel = await channels.create_chat_session_channel(guild, my_player_id, channel_name)
	channel_id = str(channel.id)
	clickable_channel_ref = channels.clickable_channel_ref(channel)

	# channel ID -> chat mapping
	chat_channel_data = ChatChannelData(channel_id, chat_name, my_player_id, my_handle)
	chats[chat_channel_data_index][channel_id] = chat_channel_data.to_string()
	# chat name -> full chat log file name mapping
	chats.write()
	print(f'Created entries in chats confobj: {chats[file_name_index][chat_name]}, {chats[chat_channel_data_index][channel_id]}')
	
	# chat -> channel ID mapping
	chat_connection = ChatConnection(chat_name, my_player_id, my_handle, channel_id)
	chat_state[chat_connection_index][my_player_id] = chat_connection
	chat_state.write()

	#test = ChatChannelData.from_string(chats[channel_id][chat_channel_data_index])
	
	print(f'Created ChatChannelData: {chat_channel_data.channel_id}, {chat_channel_data.chat_name}, {chat_channel_data.handle}, {chat_channel_data.player_id}')
	channels.init_chat_channel(channel_name)
	return clickable_channel_ref

### Messages in chat

async def process_message(message):
	guild = server.get_guild()

	sender_channel = message.channel
	chat_channel_data : ChatChannelData = get_chat_data_from_channel_id(str(sender_channel.id))

	#channels.new_post(channel_name : str, poster_id : str, message.created_at)

	#ChatChannelData for easy ref:
	#self.channel_id = channel_id
	#self.chat_name = chat_name
	#self.player_id = player_id
	#self.handle = handle

	# TODO: repost to own channel
	# TODO: repost to other channel

