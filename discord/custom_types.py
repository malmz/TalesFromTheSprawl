import simplejson


# TODO: do these correctly!
# Should use instance fields instead of class fields.
class ReactionPaymentResult:
    success = False
    report = None

class Transaction:
    success = False
    report : str = None
    timestamp = None # TODO
    amount : int = 0
    payer : str = None
    recip : str = None
    last_in_sequence : bool = True
    # cause?

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