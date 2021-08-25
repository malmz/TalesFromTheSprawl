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
	Unknown = 'NA'

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

	def get_type(self):
		return EventType.NetworkOutage


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

	def from_specific_event(event_obj, repetitions : int=1, spacing : int=0):
		return Event(event_obj.get_type(), event_obj.to_string(), repetitions=repetitions, spacing=spacing)

	@staticmethod
	def from_string(string : str):
		obj = Event(EventType.Unknown, None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)

	def to_specific_type(self):
		if self.event_type == EventType.NetworkOutage:
			return NetworkOutageEvent.from_string(self.data)
		else:
			print(f'Scenario event type {self.event_type} not implemented yet.')

	async def execute(self):
		for i in range(self.repetitions):
			if self.event_type == EventType.NetworkOutage:
				event = NetworkOutageEvent.from_string(self.data)
				game.set_network_down()
				print(f'  Network out.')
				await asyncio.sleep(event.time_in_seconds)
				game.set_network_restored()
				print(f'  Network restored.')
			else:
				print(f'  Scenario event type {self.event_type} not implemented yet.')
			print(f'  Executed repetition {i+1} out of {self.repetitions}')
			await asyncio.sleep(self.spacing)



class Scenario(object):
	def __init__(
		self,
		name : str,
		steps : List[Event] = None):
		self.name = name
		self.steps = [] if steps is None else steps

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

	async def execute(self):
		print(f'Executing scenario \"{self.name}\"...')
		for i, step in enumerate(self.steps):
			repetition_string = '' if step.repetitions == 1 else f' x{step.repetitions}'
			print(f'Executing step #{i} ({step.event_type}{repetition_string}) of scenario \"{self.name}\"...')
			await step.execute()
			print(f'Finished executing step #{i} ({step.event_type}{repetition_string}) of scenario \"{self.name}\".')
		print(f'Finished scenario \"{self.name}\".')



scenarios_conf_dir = 'scenarios'
name_index = '___name'

def store_scenario(scenario : Scenario):
	file_name = f'{scenarios_conf_dir}/{scenario.name}.conf'
	scenario_conf = ConfigObj(file_name)
	scenario_conf[name_index] = scenario.name
	for i, step in enumerate(scenario.steps):
		scenario_conf[str(i)] = scenario.steps[i].to_string()
	scenario_conf.write()

def read_scenario(name : str):
	file_name = f'{scenarios_conf_dir}/{name}.conf'
	scenario_conf = ConfigObj(file_name)
	if name_index in scenario_conf and scenario_conf[name_index] == name:
		scenario = Scenario(name)
		index = 0
		while str(index) in scenario_conf:
			scenario.steps.append(Event.from_string(scenario_conf[str(index)]))
			index += 1
		return scenario



async def create_scenario(name : str):
	if name is None:
		return 'Error: you must give a name for the scenario.'
	scenario = Scenario(name)
	scenario.steps.append(
		Event.from_specific_event(
			NetworkOutageEvent(time_in_seconds=10)
			)
		)
	store_scenario(scenario)

async def run_scenario(name : str):
	if name is None:
		return 'Error: you must give a name for the scenario.'
	scenario = read_scenario(name)
	await scenario.execute()
