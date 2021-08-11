import datetime
import posting
import common_channels
import finances
import handles
import players
import custom_types

reactions_worth_money = {'💴' : 1, '💸' : 1, '💰' : 1, '🍺' : 1, '💯' : 100}

async def remove_reaction(message, emoji, user_id : int):
	member = await message.channel.guild.fetch_member(user_id)
	if member == None:
		print(f'Error: tried to remove reaction but member not found, user_id is {user_id}')
	else:
		await message.remove_reaction(emoji, member)

class ReactionRecipientSearchResult:
    message = None
    recipient : str = None

async def find_reaction_recipient_and_message(message_id : int, channel):
	result = ReactionRecipientSearchResult()
	partial_message = channel.get_partial_message(message_id)
	#print(f'Fetched partial message {emoji} from {user_id} on message {message_id}, sent at {partial_message.created_at} in channel {channel.name}')

	epsilon = datetime.timedelta(milliseconds=500)
	timestamp = partial_message.created_at + epsilon
	message_history = await channel.history(limit=10, before=timestamp).flatten()
	result.message = message_history[0]
	for message in message_history:
		match = posting.read_handle_from_post(message.content)
		if match != None:
			#print(f'Recorded reaction on post by {match}')
			result.recipient = match
			break
	return result


async def process_reaction_add(message_id : int, user_id : str, channel, emoji):
	if common_channels.is_anonymous_channel(channel):
		# No point in acting on reactions when we can't determine the receiver
		return
	print(f'User reacted with {emoji}')

	# Currently only one use case for reading reactions, and that is for paying money
	payment_amount = 0
	emoji_str = str(emoji)
	if emoji_str in reactions_worth_money:
		payment_amount = reactions_worth_money[emoji_str]

	if payment_amount > 0:
		# If other reactions are implemented, perhaps this search will be relevant for all of them
		search_result : ReactionRecipientSearchResult = await find_reaction_recipient_and_message(message_id, channel)

		if common_channels.is_outbox(channel.name):
			# Payment reactions in outbox will be silently swallowed
			await remove_reaction(search_result.message, emoji, user_id)
		else:
			transaction : custom_types.Transaction = await finances.try_to_pay(
				channel.guild,
				user_id,
				search_result.recipient,
				payment_amount,
				from_reaction=True
			)
			if not transaction.success:
				await remove_reaction(search_result.message, emoji, user_id)
			if transaction.report != None:
				handle = handles.get_handle(user_id)
				cmd_line_channel = players.get_cmd_line_channel_for_handle(channel.guild, handle)
				await cmd_line_channel.send(transaction.report)


