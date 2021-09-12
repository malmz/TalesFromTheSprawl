#module game.py

import discord
import asyncio
from enum import Enum

import players
import channels
import player_setup
import server
import handles
from common import gm_announcements_name

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


reserved_handles = {'admin', 'system'}

def is_handle_reserved(handle_id : str):
	global reserved_handles
	return handle_id in reserved_handles

def init():
	global reserved_handles
	for handle in player_setup.get_all_reserved():
		reserved_handles.add(handle)



# Alerts:

async def check_alerts(message_string : str, channel, user_id : str):
	if 'welcome the tree of light' in message_string:
		guild = server.get_guild()
		alerts_channel = channels.get_discord_channel_from_name(guild, gm_announcements_name)
		sender = players.get_player_id(user_id)
		handle = handles.get_active_handle_id(sender)
		if handle is None:
			content = f'Sent by {sender} in {channels.clickable_channel_ref(channel)}:\n> ' + message_string
		else:
			content = f'Sent by {handle} ({sender}) in {channels.clickable_channel_ref(channel)}:\n> ' + message_string
		await alerts_channel.send(content)