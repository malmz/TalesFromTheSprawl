import datetime
import posting
import channels
import finances
import handles
import players
import custom_types
import chats


# good-to-have emojis:
# ✅
# ❇️
# ❌
# 🟥
# 🔥

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

	epsilon = datetime.timedelta(milliseconds=500)
	timestamp = partial_message.created_at + epsilon
	message_history = await channel.history(limit=20, before=timestamp).flatten()
	for message in message_history:
		if message.id == message_id:
			result.message = message
		if result.message == None:
			# We fetched a few messages that actually came after the original one (within 500 ms)
			continue
		match = posting.read_handle_from_post(message.content)
		if match != None:
			#print(f'Recorded reaction on post by {match}')
			result.recipient = match
			break
	return result

async def process_reaction_for_payment(message_id : int, user_id : int, channel, emoji):
	player_id = players.get_player_id(str(user_id))

	# Currently only one use case for reading reactions, and that is for paying money
	payment_amount = 0
	emoji_str = str(emoji)
	if emoji_str in reactions_worth_money:
		payment_amount = reactions_worth_money[emoji_str]

	if payment_amount > 0:
		# If other reactions are implemented, perhaps this search will be relevant for all of them
		search_result : ReactionRecipientSearchResult = await find_reaction_recipient_and_message(message_id, channel)

		transaction : custom_types.Transaction = await finances.try_to_pay(
			channel.guild,
			player_id,
			search_result.recipient,
			payment_amount,
			from_reaction=True
		)
		if not transaction.success:
			await remove_reaction(search_result.message, emoji, user_id)
		if transaction.report != None:
			handle = handles.get_handle(player_id)
			cmd_line_channel = players.get_cmd_line_channel_for_handle(channel.guild, handle)
			await cmd_line_channel.send(transaction.report)

async def process_reaction_in_chat_hub(message_id : int, user_id : int, channel, emoji):
	message = await channel.fetch_message(message_id)
	await chats.process_reaction_in_chat_hub(message, str(emoji))


async def process_reaction_add(message_id : int, user_id : int, channel, emoji):
	print(f'User reacted with {emoji}')
	if channels.is_anonymous_channel(channel):
		# Reactions are allowed in anonymous channels, but trigger no effects
		return
	if (channels.is_cmd_line(channel.name)
		or channels.is_finance(channel.name)
		):
		# Reactions in cmd_line and finance channels will be silently swallowed
		await remove_reaction(search_result.message, emoji, user_id)
		return

	if channels.is_chat_hub(channel.name):
		await process_reaction_in_chat_hub(message_id, user_id, channel, emoji)
	else:
		await process_reaction_for_payment(message_id, user_id, channel, emoji)


