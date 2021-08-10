import channels
import handles


### General message processing (non-command) for system bot
# Mainly implements pseudonymous and anonymous message sending
# by deleting all messages and reposting them with custom
# handles

async def repost_message(message, handle):
    if handle == None:
        post = message.content
    else:
        timestamp = message.created_at
        timestamp_str = '(' + str(timestamp.hour) + ':' + str(timestamp.minute) + ':' + str(timestamp.second) + ')'
        post = '**' + handle + '** ' + timestamp_str + ':\n' + message.content
    await message.channel.send(post)

async def process_message(message, anonymous=False):
    await message.delete()
    current_channel = str(message.channel.name)
    user_id = str(message.author.id)
    if anonymous:
        current_poster_id = user_id
        current_poster_display_name = 'Anonymous'
    else:
        handle = handles.get_handle(user_id)
        current_poster_id = handle
        current_poster_display_name = handle
    full_post = channels.new_post(current_channel, current_poster_id, message.created_at)
    if full_post:
        await repost_message(message, current_poster_display_name)
    else:
        await repost_message(message, None)