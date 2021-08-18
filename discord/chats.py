import discord
import asyncio
from configobj import ConfigObj
import simplejson

import actors
import players
import handles
import channels
import server
import posting
import actors
from common import emoji_cancel, emoji_open, emoji_green, emoji_red, emoji_unread

chats_dir = 'chats'
chats = ConfigObj(f'chats.conf')
chat_channel_budget = ConfigObj('channel_budget.conf')

channel_limit_per_actor = 6

channel_id_index = '___channel_id'
handle_index = '___handle'
chat_channel_data_index = '___chat_channel_data'
chat_hub_msg_data_index = '___chat_hub_msg_data'
chat_content_index = '___chat_content'
chats_with_logs_index = '___chat_log_length'
chat_participants_index = '___chat_participants'

session_status_active = '___active'
session_status_inactive = '___inactive'
session_status_unread = '___inactive_unread'

# TODO: support for burning a burner that was involved in a chat!

### Classes, init and basic utilities

# This is stored indexed by handle, and points out the various connections that handle has to the chat
class ChatParticipant(object):
	def __init__(self, chat_name : str, session_status : str, channel_name : str, actor_id : str, handle : str, chat_hub_msg_id : str, channel_id : str=None):
		self.chat_name = chat_name
		self.session_status = session_status
		# Regardless of whether the channel currently exists or not
		# it shall have the same name every time it's re-created
		self.channel_name = channel_name
		self.actor_id = actor_id
		self.handle = handle
		self.chat_hub_msg_id = chat_hub_msg_id
		# Set to None when the channel is temporarily closed
		self.channel_id = channel_id

	@staticmethod
	def from_string(string : str):
		obj = ChatParticipant(None, None, None, None, None, None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)


# This is stored per channel/msg ID, and maps back to the chat
class ChatConnectionMapping(object):
	def __init__(self, chat_name : str, actor_id : str, handle : str):
		self.chat_name = chat_name
		self.actor_id = actor_id
		self.handle = handle

	@staticmethod
	def from_string(string : str):
		obj = ChatConnectionMapping(None, None, None)
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

# This represent everything in discord that can currently be used to interface with the chat:
# - Channel for messages
# - The chat hub message with open/close commands
# This is not meant to be stored in any configobj
class ChatUI(object):
	def __init__(self, chat_name : str, channel, chat_hub_message, session_status : str, handle : str, actor_id : str):
		self.chat_name = chat_name
		self.channel = channel # Can be None, if the channel is closed (session_status_inactive)
		self.chat_hub_message = chat_hub_message
		self.session_status = session_status
		self.handle = handle
		self.actor_id = actor_id


def init_chats_confobj():
	if not chat_channel_data_index in chats:
		chats[chat_channel_data_index] = {}
	if not chat_hub_msg_data_index in chats:
		chats[chat_hub_msg_data_index] = {}
	if not chats_with_logs_index in chats:
		chats[chats_with_logs_index] = {}


async def init(bot, clear_all : bool=False):
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
				# Close all chat sessions. If the discord and config files are still in sync,
				# this will update all chat hub messages so that chats can be easily re-opened
				await close_chat_session(chat_state, participant)
	# Remove all channel mappings
	chats[chat_channel_data_index] = {}
	if clear_all:
		chats[chat_hub_msg_data_index] = {}
		chats[chats_with_logs_index] = {}
		await asyncio.gather(
			*[asyncio.create_task(c.purge())
			for c
			in channels.get_all_chat_hub_channels(bot)])

	# Any left-over channels after this should be deleted
	await channels.delete_all_chats(bot)
	for actor_id in chat_channel_budget:
		del chat_channel_budget[actor_id]
		chat_channel_budget.write()

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
	if channel_id in chats[chat_channel_data_index]:
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

def clear_hub_msg_connection_mapping(msg_id):
	if msg_id in chats[chat_hub_msg_data_index]:
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

def read_participant(chat_state, handle : str):
	if handle in chat_state[chat_participants_index]:
		string = chat_state[chat_participants_index][handle]
		participant : ChatParticipant = ChatParticipant.from_string(string)
		return participant
	else:
		return None

def store_participant(chat_name : str, participant : ChatParticipant):
	chat_state = get_chat_state(chat_name)
	chat_state[chat_participants_index][participant.handle] = participant.to_string()
	chat_state.write()


def get_log_length(chat_name : str):
	return int(chats[chats_with_logs_index][chat_name])

def increment_log_length(chat_name : str):
	prev_length = int(chats[chats_with_logs_index][chat_name])
	chats[chats_with_logs_index][chat_name] = str(prev_length + 1)
	chats.write()

# TODO: move the chat log to a separate file, so that writing an entry
# and opening/closing a sesson don't need to interfere

def read_chat_log_entry(chat_state, index : int):
	string = chat_state[chat_content_index][str(index)]
	return ChatLogEntry.from_string(string)

def get_chat_log_iterable(chat_state, chat_name : str):
	log_length = get_log_length(chat_name)
	for index in range(log_length):
		index_str = str(index)
		if index_str in chat_state[chat_content_index]:
			yield (index, read_chat_log_entry(chat_state, index))
		else:
			print(f'Missing value {index_str} in log for {chat_name}')

def store_chat_log_entry(chat_name : str, index : int, entry : ChatLogEntry):
	chat_state = get_chat_state(chat_name)
	chat_state[chat_content_index][str(index)] = entry.to_string()
	chat_state.write()

def remove_entry_from_chat_log(chat_state, chat_name : str, index : int):
	index_str = str(index)
	if index_str in chat_state[chat_content_index]:
		# Re-read the log (minimize time between read and write)
		chat_state = get_chat_state(chat_name)
		del chat_state[chat_content_index][index_str]
		chat_state.write()

def write_new_chat_log_entry(chat_name : str, entry : ChatLogEntry):
	next_index = get_log_length(chat_name)
	store_chat_log_entry(chat_name, next_index, entry)
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


### The channel budget

def try_to_add_active_chat(actor_id : str):
	if actor_id in chat_channel_budget:
		prev_number = int(chat_channel_budget[actor_id])
		if prev_number < channel_limit_per_actor:
			chat_channel_budget[actor_id] = str(prev_number + 1)
			chat_channel_budget.write()
			return True
		else:
			return False
	else:
		chat_channel_budget[actor_id] = 1
		chat_channel_budget.write()
		return True

def decrease_num_active_chats(actor_id : str):
	if actor_id in chat_channel_budget:
		prev_number = int(chat_channel_budget[actor_id])
		if prev_number > 0:
			chat_channel_budget[actor_id] = str(prev_number - 1)
			chat_channel_budget.write()
	else:
		chat_channel_budget[actor_id] = 0
		chat_channel_budget.write()


### Creating a new chat

# TODO: Split this into create_2party_chat and create_chat, where the latter takes my_handle and [other_handles]
async def create_2party_chat(my_handle : str, partner_handle : str):
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
	# Chat-specific config: will hold all history, but also actors' active handles and channels
	newly_created_chat = init_chat_log(chat_name)
	if newly_created_chat:
		channels.init_chat_channel(chat_name)

	guild = server.get_guild()
	chat_state = get_chat_state(chat_name)

	# TODO: if we are at the limit, we must auto-close another chat session
	# (or perhaps fail, instructing to close one manually?)

	# Always activate my own session:
	task_add_me = asyncio.create_task(
		add_participant_to_chat(
			guild,
			chat_state,
			chat_name,
			my_status.actor_id,
			my_handle,
			port_name = partner_handle,
			activate = True
		)
	)

	# For the partner, the session will not be activated.
	# We will get a reference to the UI from the partner's side as well, but it will
	# only contain a channel if we are re-opening a chat that was already open in their end
	task_add_partner = asyncio.create_task(
		add_participant_to_chat(
			guild,
			chat_state,
			chat_name,
			partner_status.actor_id,
			partner_handle,
			port_name = my_handle
		)
	)

	[my_ui, partner_ui] = await asyncio.gather(task_add_me, task_add_partner)
	if my_ui.channel is None:
		clickable_chat_hub = channels.clickable_channel_ref(get_chat_hub_channel(my_status.actor_id))
		report = (f'Created chat {chat_name}, but it is currently closed since you have too many chat sessions open. '
			+ f'You can access the chat from {clickable_chat_hub}, if you close another chat first.')
		return report
	my_clickable_ref = channels.clickable_channel_ref(my_ui.channel)
	partner_clickable_ref = channels.clickable_channel_ref(my_ui.channel) if partner_ui.channel is not None else None

	if not newly_created_chat:
		report = f'Re-opened chat between {my_handle} and {partner_handle}: {my_clickable_ref}'
		if partner_clickable_ref is not None:
			# TODO: this is only here during testing
			# non-admins should not see their partner's channel even if it does exist.
			report += f'(Other channel is available at {partner_clickable_ref})'
	elif my_status.actor_id == partner_status.actor_id:
		report = (f'Opened chat between {my_handle} and {partner_handle}. '
			+ 'Note that both handles are controlled by you, so you will be chatting with yourself. '
			)
		if partner_clickable_ref is not None:
			report += f'Channels are available at {my_clickable_ref} and {partner_clickable_ref}.'
		else:
			report += f'Channel is available at {my_clickable_ref}.'
	else:
		report = f'Opened chat between {my_handle} and {partner_handle}: {my_clickable_ref}'
	return report

async def create_chat_from_command(ctx, partner_handle):
	creator_user_id = str(ctx.message.author.id)
	creator_actor_id = players.get_player_id(creator_user_id)
	creator_handle = handles.get_handle(creator_actor_id)
	report = await create_2party_chat(creator_handle, partner_handle)
	if report != None:
		await ctx.send(report)



### Common method used both when creating and re-opening chats

async def get_chat_session_if_open(chat_state, handle : str):
	participant : ChatParticipant = read_participant(chat_state, handle)
	if (participant != None # Chat already exists
		and participant.channel_id != None # Chat not only exists, but is already open
		):
		return channels.get_discord_channel(participant.channel_id)


async def add_participant_to_chat(
	guild,
	chat_state,
	chat_name : str,
	actor_id : str,
	handle : str,
	port_name : str,
	activate : bool=False
	):
	channel_name = f'{handle}_to_{port_name}'
	
	participant : ChatParticipant = read_participant(chat_state, handle)
	if participant == None:
		# This is a newly added participant
		participant = create_new_participant(chat_name, channel_name, session_status_inactive, actor_id, handle)
	# TODO: customise further: add option to UPDATE a chat session (i.e. update the hub msg) without actually creating a channel
	return await get_chat_ui(guild, chat_state, participant, activate)

def create_new_participant(chat_name : str, channel_name : str, session_status : str, actor_id : str, handle : str):
	return ChatParticipant(
		chat_name,
		session_status,
		channel_name,
		actor_id,
		handle,
		chat_hub_msg_id=None,
		channel_id=None)

async def get_chat_ui(guild, chat_state, participant : ChatParticipant, activate : bool):
	# Chat already exists
	if participant.session_status == session_status_active:
		# Chat not only exists, but is already open
		return await get_chat_ui_for_active_session(guild, participant)
	else:
		# Chat exists but channel has been closed
		return await get_chat_ui_for_inactive_session(
			guild,
			chat_state,
			participant,
			activate
		)


async def get_chat_ui_for_active_session(guild, participant):
	if participant.channel_id is None or participant.chat_hub_msg_id is None:
		raise RuntimeError(f'Chat session {participant.handle} : {participant.chat_name} is listed as active, '
			+ 'but missing either channel_id or chat_hub_msg_id'
		)
	chat_channel = channels.get_discord_channel(participant.channel_id)

	chat_hub_channel = actors.get_chat_hub_channel(participant.actor_id)
	chat_hub_message = await chat_hub_channel.fetch_message(participant.chat_hub_msg_id)

	return ChatUI(
		participant.chat_name,
		chat_channel,
		chat_hub_message,
		participant.session_status,
		participant.handle,
		participant.actor_id)


async def get_chat_ui_for_inactive_session(guild, chat_state, participant : ChatParticipant, activate : bool):
	if participant.session_status == session_status_active or participant.channel_id is not None:
		raise RuntimeError(f'Instructed to open session but it appears to be active. Dump: {participant.to_string()}')

	channel = None

	# TODO: we also need to check if there is room to create another channel
	# If there is not, we should fail activation, and adapt the hub msg accordingly
	status_change = False
	if activate:
		can_be_activated = try_to_add_active_chat(participant.actor_id)
		if can_be_activated:
			channel = await create_channel_for_chat_session(guild, chat_state, participant)
			participant.channel_id = str(channel.id)
			# channel ID -> chat mapping
			participant.session_status = session_status_active
			chat_connection = ChatConnectionMapping(participant.chat_name, participant.actor_id, participant.handle)
			store_chat_connection_for_channel(participant.channel_id, chat_connection)
			status_change = True

	chat_hub_message = await update_chat_hub_message(guild, channel, participant, has_changed=status_change)
	participant.chat_hub_msg_id = str(chat_hub_message.id)

	# chat -> actor, channel ID, msg ID mapping
	# 'participant' may have been updated: 
	store_participant(participant.chat_name, participant)

	return ChatUI(
		participant.chat_name,
		channel,
		chat_hub_message,
		participant.session_status,
		participant.handle,
		participant.actor_id
	)

async def create_channel_for_chat_session(guild, chat_state, participant : ChatParticipant):
	channel = await channels.create_chat_session_channel_no_role(guild, participant.channel_name)
	await channel.send(
		(
			f'```This is the start of {participant.channel_name}. '
			+ f'In this chat, you will always appear as \"{participant.handle}\", even if you switch handles elsewhere.```'
		)
	)

	await repost_message_history(channel, chat_state, participant)

	# At this point we want to give permissions (prevent unread from before)
	await actors.give_actor_access(guild, channel, participant.actor_id)
	return channel

async def open_chat_from_reaction(chat_state, participant : ChatParticipant):
	guild = server.get_guild()
	# activate the session:
	chat_ui = await get_chat_ui(guild, chat_state, participant, activate=True)
	return chat_ui.session_status == session_status_active


### The messages in the chat_hub channel, which are linked to and from the chat state itself

def generate_hub_msg_active_session(discord_channel, handle : str):
	clickable_ref = channels.clickable_channel_ref(discord_channel)
	content = (f'> Chat name: {clickable_ref}\n'
		+ f'> Your identity: **{handle}**\n'
		+ f'> Status: {emoji_green}  **connected**\n'
		+ f'> To close connection, click on the {emoji_cancel} below.'
	)
	return content

def generate_hub_msg_inactive_session(chat_title : str, handle : str):
	content = (f'> Chat name: **{chat_title}**\n'
		+ f'> Your identity: **{handle}**\n'
		+ f'> Status: {emoji_red}  **not connected** (no unread messages)\n' # TODO
		+ f'> To open connection, click on the {emoji_open} below.'
	)
	return content

def generate_hub_msg_unread_session(chat_title : str, handle : str):
	content = (f'> Chat name: **{chat_title}**\n'
		+ f'> Your identity: **{handle}**\n'
		+ f'> Status: {emoji_red} {emoji_unread} **not connected – unread messages** \n' # TODO
		+ f'> To open connection, click on the {emoji_open} below.'
	)
	return content

def generate_hub_msg(handle : str, session_status : str, chat_title : str=None, discord_channel=None):
	if session_status == session_status_active:
		if discord_channel is None:
			raise RuntimeError(f'Attempted to write chat hub msg for active session, but there is no channel. Dump: {participant.to_string()}')
		return generate_hub_msg_active_session(discord_channel, handle)
	elif session_status == session_status_inactive:
		return generate_hub_msg_inactive_session(chat_title, handle)
	elif session_status == session_status_unread:
		return generate_hub_msg_unread_session(chat_title, handle)

async def update_chat_hub_message(guild, chat_channel, participant, has_changed : bool=False, repost : bool=False):
	message = None
	chat_hub_channel = actors.get_chat_hub_channel(participant.actor_id)
	if participant.chat_hub_msg_id is not None:
		try:
			message = await chat_hub_channel.fetch_message(participant.chat_hub_msg_id)
		except discord.errors.NotFound:
			# No message found -- we will create a new one
			pass

	if message is None or has_changed:
		# TODO: with multi-part chats, the title should be the chat name
		# but for 2party ones it should be the channel name
		new_content = generate_hub_msg(participant.handle, participant.session_status, participant.channel_name, chat_channel)
		if message is None:
			message = await chat_hub_channel.send(new_content)
		elif repost:
			# Delete the message and post a new one -- will make sure it shows up as unread
			clear_hub_msg_connection_mapping(str(message.id))
			await message.delete()
			message = await chat_hub_channel.send(new_content)
		else:
			# Pre-existing message, but we must update it
			edit_task = asyncio.create_task(message.edit(content=new_content))
			clear_reactions_task = asyncio.create_task(message.clear_reactions())
			await asyncio.gather(edit_task, clear_reactions_task)
	await add_initial_reaction_chat_hub_msg(message, participant.session_status)

	chat_connection = ChatConnectionMapping(participant.chat_name, participant.actor_id, participant.handle)
	store_chat_connection_for_hub_msg(str(message.id), chat_connection)

	return message

async def add_initial_reaction_chat_hub_msg(message, session_status : str):
	initial_emoji = emoji_open if session_status != session_status_active else emoji_cancel
	await message.add_reaction(initial_emoji)

async def process_reaction_in_chat_hub(message, emoji : str):
	print(f'Got reaction: {message.id}, {message.content}, {emoji}')

	await message.clear_reaction(emoji)

	message_id = str(message.id)

	chat_connection : ChatConnectionMapping = read_chat_connection_from_hub_msg(message_id)
	if chat_connection == None:
		print('Error: reacted to old message in chat hub, not connected to any active chat.')
		return

	chat_state = get_chat_state(chat_connection.chat_name)
	participant : ChatParticipant = read_participant(chat_state, chat_connection.handle)

	if (participant.session_status == session_status_active
		and emoji == emoji_cancel
		):
		await close_session_from_reaction(chat_state, participant)
	elif (participant.session_status != session_status_active
		and emoji == emoji_open
		):
		success = await open_chat_from_reaction(chat_state, participant)
		if not success:
			warning = f'Cannot open {chat_connection.chat_name} -- you have too many open chats! Close one before opening another.'
			await message.channel.send(content = warning, delete_after=6)



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

	chat_state = get_chat_state(chat_name)
	participant : ChatParticipant = read_participant(chat_state, my_handle)

	failure_report = await close_chat_session(chat_state, participant)
	if failure_report is None:
		return f'Closed chat session with {partner_handle}. To re-open, use \".chat {partner_handle}\".'
	else:
		return failure_report


async def close_chat_session(chat_state, participant : ChatParticipant):
	print(f'Trying to close {participant.chat_name}, for {participant.handle}')
	guild = server.get_guild()
	chat_state = get_chat_state(participant.chat_name)

	# update chat -> channel ID mapping
	if participant.session_status != session_status_active:
		return f'Tried to close {participant.chat_name} for {participant.handle} but the session was not open.'

	if participant.channel_id is None:
		raise RuntimeError(f'Attempted to close {participant.chat_name} for {participant.handle}, recorded as active, '
			+'but channel ID is missing. Dump: {participant.to_string()}'
		)

	decrease_num_active_chats(participant.actor_id)

	channel_id_to_close = participant.channel_id

	# Remove channel ID -> chat mapping
	clear_channel_connection_mappings(channel_id_to_close)

	# Update participant
	participant.channel_id = None
	participant.session_status = session_status_inactive

	# Close the session, i.e. delete the actor's discord channel
	await channels.delete_discord_channel(channel_id_to_close)

	chat_hub_message = await update_chat_hub_message(guild, None, participant, has_changed=True)
	participant.chat_hub_msg_id = str(chat_hub_message.id)

	# 'participant' is the chat -> actor, channel ID, msg ID mapping
	store_participant(participant.chat_name, participant)

	# Add chat log entry for this event
	entry = ChatLogEntry(None, closed_handle=participant.handle)
	write_new_chat_log_entry(participant.chat_name, entry)

async def close_chat_session_from_command(ctx, partner_handle : str):
	my_user_id = str(ctx.message.author.id)
	my_actor_id = actors.get_actor_id(my_user_id)
	my_handle = handles.get_handle(my_actor_id)
	report = await close_2party_chat_session(my_handle, partner_handle)
	if report != None:
		await ctx.send(report)

async def close_session_from_reaction(chat_state, participant : ChatParticipant):
	# Ignore return value -- there is no channel to send it to
	await close_chat_session(chat_state, participant)



### Messages in chat

async def post_to_participant(guild, chat_state, message, participant : ChatParticipant, sender_handle : str, full_post : bool):
	if participant.session_status != session_status_active:
		# A new channel may be created => we should always include the full header on the first message
		full_post = True

	# Try to activate the session for the recipient
	chat_ui = await get_chat_ui(guild, chat_state, participant, activate=True)
	if chat_ui.session_status == session_status_active:
		if chat_ui.channel is None:
			print(f'Failed to reach participant of chat. Dump: {participant.to_string()}')
		else:
			# Send the message to the open channel
			poster_id = sender_handle if full_post else None
			await posting.repost_message_to_channel(chat_ui.channel, message, poster_id)
	elif chat_ui.session_status == session_status_inactive:
		# The channel was not opened when requested -- recipient must be at their chat session limit
		participant.session_status = session_status_unread
		# Update and repost the chat hub message:
		chat_hub_message = await update_chat_hub_message(guild, chat_ui.channel, participant, has_changed=True, repost=True)
		participant.chat_hub_msg_id = str(chat_hub_message.id)
		# chat -> (actor, channel ID, msg ID mapping) has been updated
		store_participant(participant.chat_name, participant)
	elif chat_ui.session_status == session_status_unread:
		# Chat already has unread messages -- nothing changes when we add one more
		pass
	else:
		raise RuntimeError(f'Unexpected case! Dump: {participant.to_string()}, {chat_ui.session_status}')


def create_reposting_tasks(guild, chat_name : str, message, sender_handle : str, full_post : bool):
	chat_state = get_chat_state(chat_name)
	for participant in get_participants(chat_state):
		yield asyncio.create_task(post_to_participant(guild, chat_state, message, participant, sender_handle, full_post))

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

async def repost_string_buffer(channel, string_buffer : str):
	if string_buffer != '':
		await channel.send(string_buffer)
		string_buffer = ''
	return string_buffer

async def repost_message_history(channel, chat_state, participant : ChatParticipant):
	any_history = False
	index_to_remove : int = -1
	# each entry is a ChatLogEntry
	string_buffer = ''
	for (index, entry) in get_chat_log_iterable(chat_state, participant.chat_name):
		if (entry.closed_handle is not None
			and entry.closed_handle == participant.handle
			and any_history):
			# This entry denotes the point where closed_handle stopped listening
			# and there has been history before this point.
			# Empty the current buffer:
			string_buffer = await repost_string_buffer(channel, string_buffer)
			# Print delimiter:
			await channel.send(
				f'```====== last chat session was closed here ======```'
			)
			index_to_remove = index
		elif entry.message is not None:
			any_history = True
			if entry.header:
				# Send the buffer we have built up so far
				string_buffer = await repost_string_buffer(channel, string_buffer)
			if string_buffer == '':
				string_buffer = entry.message
			else:
				string_buffer += f'\n{entry.message}'
	# Finish by sending anything that is left over
	await repost_string_buffer(channel, string_buffer)
	if any_history:
		await channel.send(
			f'```====== re-opened chat {participant.channel_name} ======```'
		)

	# Remove the entry that denoted last time session was closed
	# TODO: chat_log_length_at_last_close could also be tracked on a participant level
	# would probably be cleaner
	if index_to_remove != -1:
		remove_entry_from_chat_log(chat_state, participant.chat_name, index_to_remove)
		
