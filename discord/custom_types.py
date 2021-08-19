import simplejson
from enum import Enum
from typing import List, Set

class ActionResult(object):
	def __init__(self, success : bool=False, report : str = None):
		self.success = success
		self.report = report

class TransTypes(Enum):
	Transfer = 1
	Collect = 2
	Burn = 3
	ChatReact = 4
	ShopOrder = 5

class Transaction(object):
	def __init__(
		self,
		payer : str,
		recip : str,
		payer_actor : str,
		recip_actor : str,
		amount : int,
		cause : TransTypes=TransTypes.Transfer,
		report : str=None,
		timestamp=None, # TODO
		success : bool=False,
		last_in_sequence : bool=True,
		emoji : str=None
		):
		self.payer = payer
		self.recip = recip
		self.payer_actor = payer_actor
		self.recip_actor = recip_actor
		self.amount = amount
		self.cause = cause
		self.report = report
		self.timestamp = timestamp
		self.success = success
		self.last_in_sequence = last_in_sequence
		self.emoji = emoji

class PostTimestamp(object):
	def __init__(self, hour : int, minute : int):
		self.hour = hour
		self.minute = minute

	def __eq__(self, other):
		if isinstance(other, self.__class__):
			return self.__dict__ == other.__dict__
		else:
			return False

	@staticmethod
	def from_string(string : str):
		obj = PostTimestamp(0, 0)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)

class ChannelIdentifier(object):
	def __init__(self, discord_channel_id : str = None, chat_channel_name : str = None):
		self.discord_channel_id = discord_channel_id
		self.chat_channel_name = chat_channel_name

	@staticmethod
	def from_string(string : str):
		obj = ChannelIdentifier()
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)


class Actor(object):
	def __init__(
		self,
		actor_index : str,
		actor_id : str,
		finance_channel_id : int,
		finance_stmt_msg_id : int,
		chat_channel_id : int):
		self.actor_index = actor_index
		self.actor_id = actor_id
		self.finance_channel_id = finance_channel_id
		self.finance_stmt_msg_id = finance_stmt_msg_id
		self.chat_channel_id = chat_channel_id


	@staticmethod
	def from_string(string : str):
		obj = Actor(None, None, 0, 0, 0)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)


class PlayerData(object):
	def __init__(
		self,
		player_id : str,
		cmd_line_channel_id : int,
		shops : List[str] = [],
		groups : List[str] = []):
		self.player_id = player_id
		self.cmd_line_channel_id = cmd_line_channel_id
		self.shops = shops
		self.groups = groups

	@staticmethod
	def from_string(string : str):
		obj = PlayerData(None, 0)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)

class HandleTypes(str, Enum):
	Unused = 'unused'
	Regular = 'regular'
	Burner = 'burner'
	Burnt = 'burnt'
	NPC = 'npc'


class Handle(object):
	def __init__(
		self,
		handle_id : str,
		handle_type : HandleTypes = HandleTypes.Unused,
		actor_id : str=None):
		self.handle_id = handle_id.lower() if handle_id is not None else None
		self.handle_type = handle_type
		self.actor_id = actor_id

	@staticmethod
	def from_string(string : str):
		obj = Handle(None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)
