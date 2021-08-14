import discord
import asyncio
from configobj import ConfigObj
import simplejson

import players
import handles
import channels
import server
import posting
from constants import emoji_cancel, emoji_open

chats_dir = 'chats'
chats = ConfigObj(f'chats.conf')

channel_id_index = '___channel_id'
handle_index = '___handle'
player_id_index = '___player_id'
chat_channel_data_index = '___chat_channel_data'
chat_hub_msg_data_index = '___chat_hub_msg_data'
chat_content_index = '___chat_content'
chats_with_logs_index = '___chat_log_length'
chat_participants_index = '___chat_participants'

session_status_active = '___active'
session_status_inactive = '___inactive'
#session_status_muted = '___muted'

### Classes, init and basic utilities

# This is stored indexed by player (TODO: handle), and points out the various connections that player has to the chat
class ChatParticipant(object):
	def __init__(self, chat_name : str, channel_name : str, player_id : str, handle : str, chat_hub_msg_id : str, channel_id : str=None):
		self.chat_name = chat_name
		# Regardless of whether the channel currently exists or not
		# it shall have the same name every time it's re-created
		self.channel_name = channel_name
		self.player_id = player_id
		self.handle = handle
		self.chat_hub_msg_id = chat_hub_msg_id
		# Set to None when the channel is temporarily closed
		self.channel_id = channel_id
		#TODO: message_id pointing to a message in player's cmd_line or similar, with open/close buttons

	@staticmethod
	def from_string(string : str):
		obj = ChatParticipant(None, None, None, None, None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)


# This is stored per channel/msg ID, and maps back to the chat
class ChatConnectionMapping(object):
	def __init__(self, chat_name : str, player_id : str, handle : str, session_status : str):
		self.chat_name = chat_name
		self.player_id = player_id
		self.handle = handle
		self.session_status = session_status

	@staticmethod
	def from_string(string : str):
		obj = ChatConnectionMapping(None, None, None, None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)

class ChatLogEntry(object):
	def __init__(self, message : str, header : bool=False, closed_handle : str=None):
		self.message = message
		self.header = header
		self.closed_handle = closed_handle

	@staticmethod
	def from_string(string : str):
		obj = ChatLogEntry(None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)

def init_chats_confobj():
	if not chat_channel_data_index in chats:
		chats[chat_channel_data_index] = {}
	if not chat_hub_msg_data_index in chats:
		chats[chat_hub_msg_data_index] = {}
	if not chats_with_logs_index in chats:
		chats[chats_with_logs_index] = {}	


async def init(bot, clear_all : bool=False):
	# Always delete all channels
	await channels.delete_all_chats(bot)

	init_chats_confobj()
	# Loop through all chats that are supposed to exist according to conf files
	for chat_name in chats[chats_with_logs_index]:
		chat_state = get_chat_state(chat_name)
		if clear_all:
			del chat_state[chat_participants_index]
			del chat_state[chat_content_index]
			chat_state.write()
		else:
			# Re-init the chats (posting-wise) like any open channel
			channels.init_chat_channel(chat_name)
			# Keep the participants data but reset the channel IDs, to indicate that all discord channels are deleted
			if not chat_participants_index in chat_state:
				init_chat_state(chat_state)
			for participant in get_participants(chat_state):
				participant.channel_id = None
				store_participant(chat_state, player_id, participant)
	if clear_all:
		chats[chat_channel_data_index] = {}
		chats[chat_hub_msg_data_index] = {}
		chats[chats_with_logs_index] = {}

	chats.write()


def create_2party_chat_name(handle1 : str, handle2 : str):
	handles_ordered = sorted([handle1, handle2])
	return f'{handles_ordered[0]}_{handles_ordered[1]}'


def read_chat_connection_from_channel(channel_id : str):
	if channel_id in chats[chat_channel_data_index]:
		string = chats[chat_channel_data_index][channel_id]
		chat_connection : ChatConnectionMapping = ChatConnectionMapping.from_string(string)
		return chat_connection
	else:
		return None

def store_chat_connection_for_channel(channel_id : str, chat_connection : ChatConnectionMapping):
	chats[chat_channel_data_index][channel_id] = chat_connection.to_string()
	chats.write()

def clear_channel_connection_mappings(channel_id):
	del chats[chat_channel_data_index][channel_id]
	chats.write()


def read_chat_connection_from_hub_msg(msg_id : str):
	if msg_id in chats[chat_hub_msg_data_index]:
		string = chats[chat_hub_msg_data_index][msg_id]
		chat_connection : ChatConnectionMapping = ChatConnectionMapping.from_string(string)
		return chat_connection
	else:
		return None

def store_chat_connection_for_hub_msg(msg_id : str, chat_connection : ChatConnectionMapping):
	chats[chat_hub_msg_data_index][msg_id] = chat_connection.to_string()
	chats.write()

def clear_hub_msg_connection_mappings(msg_id):
	del chats[chat_hub_msg_data_index][msg_id]
	chats.write()



def chat_exists(chat_name : str):
	return chat_name in chats[chats_with_logs_index]

def get_chat_state(chat_name : str):
	chat_file_name = f'{chat_name}.conf'
	return ConfigObj(f'{chats_dir}/{chat_file_name}')

def get_participants(chat_state):
	for participant_id in chat_state[chat_participants_index]:
		yield read_participant(chat_state, participant_id)

# TODO: use handle instead of player_id to index chat participants
def read_participant(chat_state, player_id : str):
	if player_id in chat_state[chat_participants_index]:
		string = chat_state[chat_participants_index][player_id]
		participant : ChatParticipant = ChatParticipant.from_string(string)
		return participant
	else:
		return None

def store_participant(chat_state, player_id : str, participant : ChatParticipant):
	chat_state[chat_participants_index][player_id] = participant.to_string()
	chat_state.write()


def get_log_length(chat_name : str):
	return int(chats[chats_with_logs_index][chat_name])

def increment_log_length(chat_name : str):
	prev_length = int(chats[chats_with_logs_index][chat_name])
	chats[chats_with_logs_index][chat_name] = str(prev_length + 1)
	chats.write()

def read_chat_log_entry(chat_state, index : int):
	string = chat_state[chat_content_index][str(index)]
	return ChatLogEntry.from_string(string)

def get_chat_log_iterable(chat_name : str):
	chat_state = get_chat_state(chat_name)
	log_length = get_log_length(chat_name)
	for index in range(log_length):
		index_str = str(index)
		if index_str in chat_state[chat_content_index]:
			yield read_chat_log_entry(chat_state, index)
		else:
			print(f'Missing value {index_str} in log for {chat_name}')

def store_chat_log_entry(chat_state, index : int, entry : ChatLogEntry):
	chat_state[chat_content_index][str(index)] = entry.to_string()
	chat_state.write()

def remove_entry_from_chat_log(chat_state, index : int):
	index_str = str(index)
	if index_str in chat_state[chat_content_index]:
		del chat_state[chat_content_index][index_str]
	chat_state.write()

def write_new_chat_log_entry(chat_name : str, entry : ChatLogEntry):
	chat_state = get_chat_state(chat_name)
	next_index = get_log_length(chat_name)
	store_chat_log_entry(chat_state, next_index, entry)
	increment_log_length(chat_name)


# Returns True if the chat was newly created, False if it already existed
def init_chat_log(chat_name : str):
	if not chat_name in chats[chats_with_logs_index]:
		chats[chats_with_logs_index][chat_name] = 0
		chats.write()
		chat_state = get_chat_state(chat_name)
		init_chat_state(chat_state)
		return True
	else:
		return False
	
def init_chat_state(chat_state):
	if not chat_participants_index in chat_state:
		chat_state[chat_participants_index] = {}
		chat_state[chat_content_index] = {}
		chat_state.write()
	else:
		print(f'Overwriting existing chat log file - the record did not indicate that chat {chat_state.filename} would exist.')

def get_chat_log_length(chat_name):
	return int(chats[chats_with_logs_index][chat_name])


### Creating a new chat

async def create_chat(my_handle : str, partner_handle : str):
	my_status : handles.HandleStatus = handles.get_handle_status(my_handle)
	if not my_status.exists:
		raise RuntimeError(f'Tried to open chat but initiator handle {my_handle} does not exist.')

	if my_handle == partner_handle:
		return f'Error: {partner_handle} is your current handle – cannot open chat with yourself.'

	partner_status : handles.HandleStatus = handles.get_handle_status(partner_handle)
	if not partner_status.exists:
		return f'Error: could not open chat with {partner_handle}; recipient does not exist.'

	# data common to both participants:
	chat_name = create_2party_chat_name(my_handle, partner_handle)
	# Chat-specific config: will hold all history, but also players' active handles and channels
	newly_created_chat = init_chat_log(chat_name)
	if newly_created_chat:
		channels.init_chat_channel(chat_name)

	guild = server.get_guild()
	chat_state = get_chat_state(chat_name)


	# Always open (or re-open) my own session:
	task_open_session_for_me = asyncio.create_task(
		open_chat_session(
			guild,
			chat_state,
			chat_name,
			my_status.player_id,
			my_handle,
			partner_handle,
			create_channel = True
		)
	)

	task_open_session_for_partner = asyncio.create_task(
		open_chat_session(
			guild,
			chat_state,
			chat_name,
			partner_status.player_id,
			partner_handle,
			my_handle
		)
	)

	# For the partner, the channel will not be auto-created. If we are re-opening an existing chat,
	# and the channel is open, we want a reference to it for the success message
	#task_open_session_for_partner = asyncio.create_task(
	#	get_chat_session_if_open(chat_state, partner_status.player_id)
	#)

	new_channels = await asyncio.gather(task_open_session_for_me, task_open_session_for_partner)
	clickable_refs = [channels.clickable_channel_ref(c) for c in new_channels if not c is None]
	if not newly_created_chat:
		report = f'Re-opened chat between {my_handle} and {partner_handle}: {clickable_refs[0]}'
		if len(clickable_refs) > 1:
			# TODO: this is only here during testing
			# non-admins should not see their partner's channel even if it does exist.
			report += f'(Other channel is avaialable at {clickable_refs[1]})'
	elif my_status.player_id == partner_status.player_id:
		report = (f'Opened chat between {my_handle} and {partner_handle}. '
			+ 'Note that both handles are controlled by you, so you will be chatting with yourself. '
			)
		if len(clickable_refs) > 1:
			report += f'Channels are available at {clickable_refs[0]} and {clickable_refs[1]}.'
		else:
			report += f'Channel is available at {clickable_refs[0]}.'
	else:
		report = f'Opened chat between {my_handle} and {partner_handle}: {clickable_refs[0]}'
	return report

async def create_chat_from_command(ctx, partner_handle):
	creator_user_id = str(ctx.message.author.id)
	creator_player_id = players.get_player_id(creator_user_id)
	creator_handle = handles.get_handle(creator_player_id)
	report = await create_chat(creator_handle, partner_handle)
	if report != None:
		await ctx.send(report)


### Common method used both when creating and re-opening chats

async def get_chat_session_if_open(chat_state, my_player_id : str):
	participant : ChatParticipant = read_participant(chat_state, my_player_id)
	if (participant != None # Chat already exists
		and participant.channel_id != None # Chat not only exists, but is already open
		):
		return channels.get_discord_channel(participant.channel_id)


async def open_chat_session(
	guild,
	chat_state,
	chat_name : str,
	my_player_id : str,
	my_handle : str,
	partner_handle : str,
	create_channel : bool=False
	):
	# TODO: for creator, this might mean closing another chat (but check for that before creating?)
	# TODO: when reopening an existing chat, we should FIRST post all the message history, 
	# and THEN add the role to give visibility
	channel_name = f'{my_handle}_to_{partner_handle}'
	
	participant : ChatParticipant = read_participant(chat_state, my_player_id)
	if participant == None:
		# This is a newly added participant
		return await create_chat_session(guild, chat_state, chat_name, channel_name, my_player_id, my_handle, create_channel)
	else:
		# Chat session already exists, but may not be open
		# TODO: customise further: add option to UPDATE a chat session (i.e. update the hub msg) without actually creating a channel
		return await open_chat_session_for_current_participant(guild, chat_state, participant, create_channel)


async def open_chat_session_for_current_participant(guild, chat_state, participant : ChatParticipant, create_channel : bool):
	# Chat already exists
	if participant.channel_id != None:
		# Chat not only exists, but is already open
		return channels.get_discord_channel(participant.channel_id)
	else:
		# Chat exists but channel has been closed
		return await reopen_chat_session(
			guild,
			chat_state,
			participant.chat_name,
			participant.channel_name,
			participant.player_id,
			participant.handle,
			create_channel
		)



# TODO: implement limit on open chat sessions!

async def create_chat_session(
	guild,
	chat_state,
	chat_name : str,
	channel_name : str,
	my_player_id : str,
	my_handle : str,
	create_channel : bool):

	chat_connection = ChatConnectionMapping(chat_name, my_player_id, my_handle, session_status_inactive)
	channel = None
	if create_channel:
		channel = await channels.create_chat_session_channel(guild, my_player_id, channel_name)
		await channel.send(
			f'```This is the start of {channel_name}. In this chat, you will always appear as \"{my_handle}\", even if you switch handles elsewhere.```'
			)
		channel_id = str(channel.id)

		# channel ID -> chat mapping
		store_chat_connection_for_channel(channel_id, chat_connection)	# chat name -> full chat log file name mapping
		chats.write()
		chat_connection.session_status = session_status_active
	else:
		channel_id = None

	chat_hub_msg_id = await create_chat_hub_message(guild, channel, my_player_id, my_handle)

	# message ID -> chat mapping
	# We have posted a new chat hub message, so must add its mapping
	store_chat_connection_for_hub_msg(chat_hub_msg_id, chat_connection)	# chat name -> full chat log file name mapping
	chats.write()

	# chat -> channel ID, msg ID mapping
	# Both channel ID (may be None) and msg ID are new
	participant = ChatParticipant(chat_name, channel_name, my_player_id, my_handle, chat_hub_msg_id, channel_id)
	store_participant(chat_state, my_player_id, participant)
	chat_state.write()

	# May return None
	return channel


# TODO: merge this with open_chat_session
# Add a "reopening" parameter to it, giving four options:
# 1. New participant, yes create channel (creator at start)
# 2. New participant, no create channel (partner at start)
# 3. Old participant, yes create channel (creator at re-opening, partner at message)
# 4. Old participant, no create channel (partner at re-opening)
async def reopen_chat_session(
	guild,
	chat_state,
	chat_name : str,
	channel_name : str,
	my_player_id : str,
	my_handle : str,
	create_channel : bool):

	chat_connection = ChatConnectionMapping(chat_name, my_player_id, my_handle, session_status_inactive)
	channel = None
	if create_channel:
		channel = await channels.create_chat_session_channel(guild, my_player_id, channel_name)
		channel_id = str(channel.id)
		await channel.send(
			f'```This is the start of {channel_name}. In this chat, you will always appear as \"{my_handle}\", even if you switch handles elsewhere.```'
			)
		any_history = await repost_message_history(channel, chat_name)
		if any_history:
			await channel.send(
				f'```====== re-opened chat {channel_name} ======```'
				)

		# channel ID -> chat mapping
		store_chat_connection_for_channel(channel_id, chat_connection)	# chat name -> full chat log file name mapping
		chats.write()
		chat_connection.session_status = session_status_active
	else:
		channel_id = None

	# TODO
	chat_hub_msg_id = '123'; #await update_chat_hub_message()

	# message ID -> chat mapping
	# We have updated (edited or deleted+reposted) our chat hub message
	# must update the mapping
	store_chat_connection_for_hub_msg(chat_hub_msg_id, chat_connection)	# chat name -> full chat log file name mapping
	chats.write()

	# chat -> channel ID, msg ID mapping
	participant = ChatParticipant(chat_name, channel_name, my_player_id, my_handle, chat_hub_msg_id, channel_id)
	store_participant(chat_state, my_player_id, participant)
	chat_state.write()

	return channel

async def open_chat_from_reaction():
	pass
	# TODO



### The messages in the chat_hub channel, which are linked to and from the chat state itself

def generate_hub_msg_active_session(discord_channel, handle : str):
	clickable_ref = channels.clickable_channel_ref(discord_channel)
	content = (f'> Chat name: {clickable_ref}\n'
		+ f'> Your identity: **{handle}**\n'
		+ '> Status: **connected**\n'
		+ f'> To close connection, click on the {emoji_cancel} below.'
	)
	return content

def generate_hub_msg_inactive_session(chat_name, handle : str):
	content = (f'> Chat name: **{chat_name}**\n'
		+ f'> Your identity: **{handle}**\n'
		+ '> Status: **not connected** (no unread messages)\n' # TODO
		+ f'> To open connection, click on the {emoji_open} below.'
	)
	return content


async def create_chat_hub_message(guild, discord_channel, player_id : str, handle : str):
	if discord_channel == None:
		content = generate_hub_msg_inactive_session(discord_channel, handle)
		initial_emoji = emoji_open
	else:
		content = generate_hub_msg_active_session(discord_channel, handle)
		initial_emoji = emoji_cancel
	chat_hub_channel = channels.get_chat_hub_channel(guild, player_id)
	message = await chat_hub_channel.send(content)
	await message.add_reaction(initial_emoji)
	return str(message.id)


#async def update_hub_msg(chat_name : str, my_handle : str, session_status : str):


async def process_reaction_in_chat_hub(message, player_id : str, emoji : str):
	print(f'Got reaction: {message.id}, {message.content}, {player_id}, {emoji}')

	await message.clear_reaction(emoji)

	message_id = str(message.id)

	chat_connection : ChatConnectionMapping = read_chat_connection_from_hub_msg(message_id)
	if chat_connection == None:
		print('Error: reacted to old message in chat hub, not connected to any active chat.')
		return
	
	if (chat_connection.session_status == session_status_active
		and emoji == emoji_cancel
		):
		await close_session_from_reaction(chat_connection)
	elif (chat_connection.session_status == session_status_inactive
		and emoji == emoji_open
		):
		await open_chat_from_reaction()



### Closing chats

async def close_2party_chat_session(my_handle : str, partner_handle : str):
	if my_handle == partner_handle:
		return f'Error: {partner_handle} is your current handle – there is no chat.'

	my_status : handles.HandleStatus = handles.get_handle_status(my_handle)
	if not my_status.exists:
		raise RuntimeError(f'Tried to close chat but initiator handle {my_handle} does not exist.')

	partner_status : handles.HandleStatus = handles.get_handle_status(partner_handle)
	if not partner_status.exists:
		return f'Error: no chat with {partner_handle} found; recipient does not exist. Check the spelling.'

	chat_name = create_2party_chat_name(my_handle, partner_handle)
	if not chat_exists(chat_name):
		return f'Error: there is no record of any chat between {my_handle} and {partner_handle}.'

	await close_chat_session(chat_name, my_handle, my_status.player_id)

	return f'Closed chat session with {partner_handle}. To re-open, use \".chat {partner_handle}\".'

async def close_chat_session(chat_name : str, my_handle : str, my_player_id : str):
	print(f'Trying to close {chat_name}, for {my_handle}/{my_player_id}')
	chat_state = get_chat_state(chat_name)

	# update chat -> channel ID mapping
	participant : ChatParticipant = read_participant(chat_state, my_player_id)
	channel_id_to_close = participant.channel_id

	# Remove channel ID -> chat mapping
	clear_channel_connection_mappings(channel_id_to_close)

	# Remove participant -> channel ID mapping
	participant.channel_id = None

	# Close the session, i.e. delete the player's discord channel
	await channels.delete_discord_channel(channel_id_to_close)

	#TODO1
	# Update chat hub message, and message ID -> chat mapping
	#hub_msg_id = await update_hub_msg(chat_name, my_handle, session_status_inactive)

	# update participant -> message ID mapping
	#participant.hub_msg_id = hub_msg_id

	store_participant(chat_state, my_player_id, participant)


async def close_chat_session_from_command(ctx, partner_handle : str):
	my_user_id = str(ctx.message.author.id)
	my_player_id = players.get_player_id(my_user_id)
	my_handle = handles.get_handle(my_player_id)
	report = await close_2party_chat_session(my_handle, partner_handle)
	if report != None:
		await ctx.send(report)

async def close_session_from_reaction(chat_connection):
	# Ignore return value -- there is no channel to send it to
	await close_chat_session(chat_connection.chat_name, chat_connection.handle, chat_connection.player_id)

### Messages in chat

async def find_chat_channel_and_post(guild, chat_state, message, participant : ChatParticipant, sender_handle : str, full_post : bool):
	if participant.channel_id == None:
		# A new channel will be created => we should always include the full header on the first message
		full_post = True
	discord_channel = await open_chat_session_for_current_participant(guild, chat_state, participant, create_channel=True)
	if discord_channel == None:
		# TODO: when the channel limit is reached, the hub msg will be updated but no channel created
		# => no channel returned
		# => we'll end up here but it will not be an error case
		raise RuntimeError(f'Could not find channel with ID {participant.channel_id}')
	else:
		poster_id = sender_handle if full_post else None
		await posting.repost_message_to_channel(discord_channel, message, poster_id)

def create_reposting_tasks(guild, chat_name : str, message, sender_handle : str, full_post : bool):
	chat_state = get_chat_state(chat_name)
	for participant in get_participants(chat_state):
		yield asyncio.create_task(find_chat_channel_and_post(guild, chat_state, message, participant, sender_handle, full_post))

async def process_message(message):
	task1 = asyncio.create_task(message.delete())

	sender_channel = message.channel
	chat_channel_data : ChatConnectionMapping = read_chat_connection_from_channel(str(sender_channel.id))
	sender_handle = chat_channel_data.handle
	chat_name = chat_channel_data.chat_name

	full_post = channels.record_new_post(chat_channel_data.chat_name, sender_handle, message.created_at)
	guild = server.get_guild()
	tasks = create_reposting_tasks(guild, chat_name, message, sender_handle, full_post)

	await asyncio.gather(task1, *tasks)

	# Write to the persistent log:
	# TODO: also add header if it is the first message after someone disconnected
	poster_id = sender_handle if full_post else None
	post = posting.create_post(message, poster_id)
	entry = ChatLogEntry(post, full_post)
	chat_state = get_chat_state(chat_name)
	write_new_chat_log_entry(chat_name, entry)

async def repost_message_history(channel, chat_name):
	history_empty = True
	# each entry is a ChatLogEntry
	string_buffer = ''
	for entry in get_chat_log_iterable(chat_name):
		if entry.message != None:
			history_empty = False
			if entry.header:
				# Send the buffer we have built up so far
				if string_buffer != '':
					await channel.send(string_buffer)
					string_buffer = ''
			if string_buffer == '':
				string_buffer = entry.message
			else:
				string_buffer += f'\n{entry.message}'
	# Finish by sending anything that is left over
	if string_buffer != '':
		await channel.send(string_buffer)
	return not history_empty
