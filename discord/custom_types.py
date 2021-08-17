import simplejson


# TODO: do these correctly!
# Should use instance fields instead of class fields.
class ReactionPaymentResult:
    success = False
    report = None

class Transaction(object):
	def __init__(
		self,
		payer : str,
		recip : str,
		amount : int,
		report : str=None,
		timestamp=None, # TODO
		success : bool=False,
		last_in_sequence : bool=True
		):
		self.payer = payer
		self.recip = recip
		self.amount = amount
		self.report = report
		self.timestamp = timestamp
		self.success = success
		self.last_in_sequence = last_in_sequence

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
		actor_id : str,
		finance_channel_id : int,
		finance_stmt_msg_id : int,
		chat_channel_id : int):
		self.actor_id = actor_id
		self.finance_channel_id = finance_channel_id
		self.finance_stmt_msg_id = finance_stmt_msg_id
		self.chat_channel_id = chat_channel_id

	@staticmethod
	def from_string(string : str):
		obj = Actor(None, 0, 0, 0)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)


class PlayerData(object):
	def __init__(
		self,
		player_id : str,
		cmd_line_channel_id : int):
		self.player_id = player_id
		self.cmd_line_channel_id = cmd_line_channel_id

	@staticmethod
	def from_string(string : str):
		obj = PlayerData(None, 0)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)


