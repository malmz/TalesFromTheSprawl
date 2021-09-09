#module game.py

import discord
import asyncio
from enum import Enum

import players
import channels
import player_setup

#Game-wide state. Only put general info here; anything specific should go in players / shops / groups / scenarios etc.

class NetworkState(str, Enum):
	NotStarted = 'not_started'
	Ready = 'ready'
	Down = 'down'


network_status = NetworkState.NotStarted


def get_network_status():
	global network_status
	return network_status

def set_network_status(new : NetworkState):
	global network_status
	network_status = new

def can_process_messages():
	return get_network_status() == NetworkState.Ready

def can_process_reactions():
	return get_network_status() == NetworkState.Ready

def start_game():
	if get_network_status() == NetworkState.NotStarted:
		set_network_status(NetworkState.Ready)
		report = 'Game started.'
	else:
		report = 'Game already started.'
	return report

def set_network_down():
	if get_network_status() != NetworkState.Down:
		set_network_status(NetworkState.Down)
	else:
		print(f'Network already down.')

def set_network_restored():
	if get_network_status() == NetworkState.Down:
		set_network_status(NetworkState.Ready)
	else:
		print(f'Network already up.')


reserved_handles = {'admin', 'gm', 'system'}

def is_handle_reserved(handle_id : str):
	global reserved_handles
	#for handle in reserved_handles:
	#	print(handle)
	#print(f'Checking: {handle_id in reserved_handles}')
	return handle_id in reserved_handles

def init():
	global reserved_handles
	for handle in player_setup.get_all_reserved():
		reserved_handles.add(handle)



# Alerts:

async def check_alerts(message_string : str, channel, user_id : str):
	if 'welcome the tree of life' in message_string:
		cmd_line_channel = players.get_cmd_line_channel('u2701')
		sender = players.get_player_id(user_id)
		content = f'Sent by {sender} in {channels.clickable_channel_ref(channel)}:\n> ' + message_string
		await cmd_line_channel.send(content)