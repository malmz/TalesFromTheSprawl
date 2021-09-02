import datetime
import posting
import channels
import finances
import players
import actors
import custom_types
import chats
import shops
import game

from custom_types import ActionResult


# good-to-have emojis:
# ✅
# ❇️
# ❌
# 🟥
# 🔥

reactions_worth_money = {'💴' : 1, '💸' : 1, '💰' : 1, '🍺' : 1, '💯' : 100, '🪙' : 1}

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

async def process_reaction_for_tipping(message_id : int, user_id : int, channel, emoji):
	player_id = players.get_player_id(str(user_id))

	# Currently only one use case for reading reactions, and that is for paying money
	payment_amount = 0
	emoji_str = str(emoji)
	if emoji_str in reactions_worth_money:
		payment_amount = reactions_worth_money[emoji_str]

	if payment_amount > 0:
		# If other reactions are implemented, perhaps this search will be relevant for all of them
		search_result : ReactionRecipientSearchResult = await find_reaction_recipient_and_message(message_id, channel)

		transaction : custom_types.Transaction = await finances.try_to_pay_from_actor(
			player_id,
			search_result.recipient,
			payment_amount,
			from_reaction=True
		)
		if not transaction.success:
			await remove_reaction(search_result.message, emoji, user_id)
		if transaction.report != None:
			cmd_line_channel = players.get_cmd_line_channel(player_id)
			await cmd_line_channel.send(transaction.report)

async def process_reaction_in_chat_hub(message_id : int, user_id : int, channel, emoji):
	message = await channel.fetch_message(message_id)
	await chats.process_reaction_in_chat_hub(message, str(emoji))

async def process_reaction_in_storefront(message_id : int, user_id : int, channel, emoji):
	message = await channel.fetch_message(message_id)
	result : ActionResult = await shops.process_reaction_in_storefront(message, str(user_id), str(emoji))
	if not result.success and result.report != None:
		player_id = players.get_player_id(str(user_id))
		cmd_line_channel = players.get_cmd_line_channel(player_id)
		if cmd_line_channel is not None:
			await cmd_line_channel.send(result.report)

	# Remove the reaction regardless of what it is
	try:
		await remove_reaction(message, emoji, user_id)
	except discord.errors.NotFound:
		pass # Ignore: it means the message was deleted so we cannot remove the reaction


async def process_reaction_in_finance_channel(message_id : int, user_id : int, channel, emoji):
	await actors.process_reaction_in_finance_channel(str(channel.id), str(message_id), str(emoji))

	# Remove the reaction regardless of what it is
	message = await channel.fetch_message(message_id)
	try:
		await remove_reaction(message, emoji, user_id)
	except discord.errors.NotFound:
		pass # Ignore: it means the message was deleted so we cannot remove the reaction

async def process_reaction_in_order_flow(message_id : int, user_id : int, channel, emoji):
	message = await channel.fetch_message(message_id)

	result : ActionResult = await shops.process_reaction_in_order_flow(str(channel.id), str(message_id), str(emoji))
	if not result.success and result.report is not None:
		await channel.send(content=result.report, delete_after=5)

	# Remove the reaction regardless of what it is
	try:
		await remove_reaction(message, emoji, user_id)
	except discord.errors.NotFound:
		pass # Ignore: it means the message was deleted so we cannot remove the reaction


reactions_timestamps = {}

async def process_reaction_add(message_id : int, user_id : int, channel, emoji):
	global reactions_timestamps
	if not game.can_process_reactions():
		# Remove the reaction
		message = await channel.fetch_message(message_id)
		await remove_reaction(message, emoji, user_id)

	# Reaction cooldown per user:
	current_time = datetime.datetime.today()
	dict_index = str(user_id)
	if dict_index in reactions_timestamps:
		prev_time = reactions_timestamps[dict_index]
		diff = current_time - prev_time
		if diff.total_seconds() < 5:
			# We cannot handle reactions from the same user too quickly after one another
			# Swallow this one, the user will have to try again.
			message = await channel.fetch_message(message_id)
			await remove_reaction(message, emoji, user_id)
			return

	reactions_timestamps[dict_index] = current_time

	print(f'User reacted with {emoji}')
	if channels.is_anonymous_channel(channel):
		# Reactions are allowed in anonymous channels, but trigger no effects
		return
	if channels.is_cmd_line(channel.name):
		# Reactions in cmd_line are silently swallowed
		message = await channel.fetch_message(message_id)
		await remove_reaction(message, emoji, user_id)
		return

	if channels.is_chat_hub(channel.name):
		await process_reaction_in_chat_hub(message_id, user_id, channel, emoji)
	elif channels.is_shop_channel(channel):
		await process_reaction_in_storefront(message_id, user_id, channel, emoji)
	elif channels.is_finance(channel.name):
		await process_reaction_in_finance_channel(message_id, user_id, channel, emoji)
	elif channels.is_order_flow(channel.name):
		await process_reaction_in_order_flow(message_id, user_id, channel, emoji)
	else:
		await process_reaction_for_tipping(message_id, user_id, channel, emoji)


