import asyncio
from configobj import ConfigObj
import simplejson

import players
import handles
import channels

chats = ConfigObj('chats/chats.conf')

file_name_index = '___file'
channel_id_index = '___channel_id'

class TestClass:
	bool_field : bool = True
	long_string : str = None

#def init():
#	chats[chat_name] = {}

async def create_chat(ctx):
	creator_user_id = str(ctx.message.author.id)
	creator_player_id = players.get_player_id(creator_user_id)

	creator_current_handle = handles.get_handle(creator_user_id)
	chat_name = f'chat_{creator_current_handle}'
	chat_file_name = f'{chat_name}.conf'

	chats[chat_name] = {}
	chats[chat_name][file_name_index] = chat_file_name

	channel_name = chat_name
	channel = await players.create_chat_channel(ctx.guild, creator_user_id, creator_player_id, channel_name)
	channel_id = channel.id
	clickable_channel_ref = channels.clickable_channel_ref(channel)
	chats[chat_name][channel_id_index] = channel_id
	
	print(f'{creator_user_id}, {creator_player_id}, {creator_current_handle}, {chat_name}, {chat_file_name}')


	chats['test'] = {}
	test_obj = TestClass()
	test_obj.long_string = 'Today I saw a daffodil'
	string = simplejson.dumps(test_obj.__dict__)
	chats['test']['1'] = string
	chats.write()

	recip_handle = 'foobar'
	report = f'Opened chat between {creator_current_handle} and {recip_handle}: {clickable_channel_ref}'
	await ctx.send(report)

async def read_chat():
	string = chats['test']['1']
	print(f'{string}')
	test_obj : TestClass = TestClass()
	test_obj.__dict__ = simplejson.loads(string)
	print(f'{test_obj.long_string}, {test_obj.bool_field}')