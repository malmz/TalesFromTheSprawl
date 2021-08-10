import common_channels
import handles
import re

### Module posting.py
# General message processing (non-command) for system bot.
# Mainly implements pseudonymous and anonymous message sending
# by deleting all messages and reposting them with custom
# handles.

post_header_regex = re.compile('^[*][*](.*)[*][*]')

def read_handle_from_post(post : str):
    matches = re.search(post_header_regex, post)
    if matches != None:
        return matches.group(1)
    else:
        return None


async def repost_message(message, handle):
    if handle == None:
        post = message.content
    else:
        timestamp = message.created_at
        # Manual DST fix:
        hour_str = str((timestamp.hour + 2) % 24)
        minute = timestamp.minute
        if minute < 10:
            minute_str = '0' + str(minute)
        else:
            minute_str = str(minute)
        second = timestamp.second
        if second < 10:
            second_str = '0' + str(second)
        else:
            second_str = str(second)
        timestamp_str = '(' + hour_str + ':' + minute_str + ':' + second_str + ')'
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