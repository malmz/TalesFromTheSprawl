#module game.py

from enum import Enum

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