
async def process_reaction_add(message_id : int, user_id : int, channel, emoji):
	partial_message = channel.get_partial_message(message_id)
	print(f'Fetched partial message {emoji} from {user_id} on message {message_id}, sent at {partial_message.created_at} in channel {channel.name}')
