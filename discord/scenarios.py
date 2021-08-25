# module scenarios.py

# This module handles the creation and execution of scenarios, which are automated sequences of in-game events.
# A scenario could be for example a simulated network crash, automated spam messages, or creation of a new group.

import discord
import asyncio
import simplejson
from configobj import ConfigObj
from enum import Enum
from typing import List
from copy import deepcopy

import players
import handles
import channels
import server
import finances
import groups
import shops
import actors
import game
from shops import Shop
from custom_types import Handle, HandleTypes, Actor, ActionResult



class EventType(str, Enum):
	NetworkOutage = 'outage'
	MessageHandles = 'msg_handles'
	MessageAllPlayersExceptHandles = 'msg_except_handles'
	MessageGroup = 'msg_groups'
	MessageExceptGroups = 'msg_except_groups'
	Unknown = 'u'

class NetworkOutageEvent(object):
	def __init__(
		self,
		time_in_seconds : int = 60
		):
		self.time_in_seconds = time_in_seconds

	@staticmethod
	def from_string(string : str):
		obj = NetworkOutageEvent()
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)	


class Event(object):
	def __init__(
		self,
		event_type : EventType,
		data : str,
		repetitions : int = 1,
		spacing : int = 0 # in seconds
		):
		self.event_type = event_type
		self.data = data
		self.repetitions = repetitions
		self.spacing = spacing

	@staticmethod
	def from_string(string : str):
		obj = Event(EventType.Unknown, None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)

	async def execute(self):
		for i in range(self.repetitions):
			if self.event_type == EventType.NetworkOutage:
				event = NetworkOutageEvent.from_string(self.data)
				game.set_network_down()
				print(f'Network out.')
				await asyncio.sleep(event.time_in_seconds)
				game.set_network_restored()
				print(f'Network restored.')
			else:
				print(f'Scenario event type {self.event_type} not implemented yet.')
			print(f'Executed repetition {i} out of {self.repetitions}')
			await asyncio.sleep(self.spacing)



class Scenario(object):
	def __init__(
		self,
		scenario_name : str,
		steps : List[Event] = []):
		self.scenario_name = scenario_name
		self.steps = steps

	@staticmethod
	def from_string(string : str):
		obj = Scenario(None)
		loaded_dict = simplejson.loads(string)
		obj.__dict__ = loaded_dict
		for i, step_str in enumerate(loaded_dict['steps']):
			obj.steps[i] = Event.from_string(step_str)
		return obj

	def to_string(self):
		dict_to_save = deepcopy(self.__dict__)
		list_of_strings = [step.to_string() for step in dict_to_save['steps']]
		dict_to_save['steps'] = list_of_strings
		return simplejson.dumps(dict_to_save)

	async def execute():
		for step in self.steps:
			await step.execute()



async def test_scenarios():
	scenario = Scenario('deus_crash')
	step_1 = NetworkOutageEvent(time_in_seconds=60)
	scenario.steps.append(Event(EventType.NetworkOutage, step_1.to_string(), repetitions=2))
	await scenario.execute()