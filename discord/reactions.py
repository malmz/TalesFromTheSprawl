import datetime
import posting
import channels
import handles

reactions_worth_money = {'💸' : 1, '💰' : 1, '🍺' : 1, '💯' : 100}

async def remove_reaction(message, emoji, user_id : int):
	if not result.success:
		member = await channel.guild.fetch_member(user_id)
		if member == None:
			print(f'Error: tried to remove reaction but member not found, user_id is {user_id}')
		else:
			await message_with_reaction.remove_reaction(emoji, member)

async def process_reaction_add(message_id : int, user_id : int, channel, emoji):
	if channels.is_anonymous_channel(channel):
		# No point in acting on reactions when we can't determine the receiver
		return

	partial_message = channel.get_partial_message(message_id)
	print(f'Fetched partial message {emoji} from {user_id} on message {message_id}, sent at {partial_message.created_at} in channel {channel.name}')

	epsilon = datetime.timedelta(milliseconds=500)
	timestamp = partial_message.created_at + epsilon
	message_history = await channel.history(limit=10, before=timestamp).flatten()
	print(f'reading all from {timestamp}')
	recipient = None
	message_with_reaction = message_history[0]
	for message in message_history:
		match = posting.read_handle_from_post(message.content)
		if match != None:
			print(f'Recorded reaction on post by {match}')
			recipient = match
			break

	payment_amount = 0
	emoji_str = str(emoji)
	if emoji_str in reactions_worth_money:
		payment_amount = reactions_worth_money[emoji_str]

	if payment_amount > 0:
		result : handles.ReactionPaymentResult = handles.try_to_pay_with_reaction(str(user_id), recipient, payment_amount)
		if not result.success:
			await remove_reaction(message_with_reaction, emoji, user_id)
		if result.report != None:
			await channel.send(result.report)


