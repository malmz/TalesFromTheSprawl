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
from shops import Shop
from custom_types import Handle, HandleTypes, Actor, ActionResult


class EventType(str, Enum):
	Disconnect = 'disconnect'
	MessageHandles = 'msg_handles'
	MessageAllPlayersExceptHandles = 'msg_except_handles'
	MessageGroup = 'msg_groups'
	MessageExceptGroups = 'msg_except_groups'
	Unknown = 'u'



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

async def test_scenarios():
	scenario = Scenario('deus_crash')
	scenario.steps.append(Event(EventType.Disconnect, 'test_data', repetitions=2))
	print(f'Event: {scenario.steps[0].to_string()}')
	print(f'Scenario: {scenario.to_string()}')
	scenario_str = scenario.to_string()
	print(f'Event from rehydrated scenario: {Scenario.from_string(scenario_str).steps[0].to_string()}')