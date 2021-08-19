import discord
import asyncio
import simplejson
from configobj import ConfigObj
from enum import Enum

import players
import handles
import channels
import server
import finances
from custom_types import Handle, HandleTypes
from common import coin


# Known_handles is meant to be read-only during the event
# It can be edited manually
known_handles = ConfigObj('known_handles.conf')

class PlayerSetupInfo(object):
	def __init__(
		self,
		handle_id : str):
		self.handle_id = handle_id
		self.other_handles = ['__example_handle1', '__example_handle2']
		self.npc_handles = ['__example_npc1', '__example_npc1']
		self.burners = ['__example_burner1', '__example_burner1']
		self.groups = ['__example_group1', '__example_group2']
		self.shops = []
		self.starting_money = 10

	@staticmethod
	def from_string(string : str):
		obj = PlayerSetupInfo(None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)



def add_known_handle(handle_id : str):
	if handle_id not in known_handles:
		known_handles[handle_id] = PlayerSetupInfo(handle_id).to_string()
		known_handles.write()
	else:
		print(f'Trying to edit player setup info for a handle that is already in the database. Please edit the file manually instead.')

def read_player_setup_info(handle_id : str):
	if handle_id in known_handles:
		return PlayerSetupInfo.from_string(known_handles[handle_id])


def reload_known_handles():
	global known_handles
	known_handles = ConfigObj('known_handles.conf')


async def player_setup_for_new_handle(handle : Handle):
	info = read_player_setup_info(handle.handle_id)
	reload_known_handles()
	if info is None:
		return None
	report = f'Loading known data for **{handle.handle_id}**...\n\n'
	any_regular = False
	for other_handle_id in info.other_handles:
		result = await handles.create_handle(handle.actor_id, other_handle_id, HandleTypes.Regular)
		if result.handle_type != HandleTypes.Unused:
			report += f'- Connected alias: regular handle **{other_handle_id}**\n'
			any_regular = True
	if any_regular:
		report += '\n'
	any_burners = False
	for other_handle_id in info.burners:
		result = await handles.create_handle(handle.actor_id, other_handle_id, HandleTypes.Burner)
		if result.handle_type != HandleTypes.Unused:
			report += f'- Connected alias: burner handle **{other_handle_id}**\n'
			any_burners = True
	if any_burners:
		report += '  (Use \".burn <burner_name>\" to destroy a burner and erase its tracks)\n\n'
	any_npcs = False
	for other_handle_id in info.npc_handles:
		result = await handles.create_handle(handle.actor_id, other_handle_id, HandleTypes.NPC)
		if result.handle_type != HandleTypes.Unused:
			report += f'  [OFF: added **{other_handle_id}** as an NPC account.]\n'
			any_npcs = True
	if any_npcs:
		report += f'  [OFF: NPC accounts let you act as someone else, and cannot be traced to your other handles.]\n\n'
	if finances.can_have_finances(handle.handle_type):
		await finances.add_funds(handle, int(info.starting_money))
		report += f'Current balance of **{handle.handle_id}**: {coin} **{info.starting_money}**\n\n'

	report += f'All data loaded. Welcome, **{handle.handle_id}**.'
	return report