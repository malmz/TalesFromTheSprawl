import channels
import handles
from constants import forbidden_content
import players

import re
import asyncio

### Module posting.py
# General message processing (non-command) for system bot.

# Common channels:
# Mainly implements pseudonymous and anonymous message sending
# by deleting all messages and reposting them with custom
# handles.

hard_space = '⠀'
double_hard_space = hard_space + hard_space

post_header_regex = re.compile(f'^[*][*](.*)[*][*]{double_hard_space}')

def read_handle_from_post(post : str):
    matches = re.search(post_header_regex, post.lower())
    if matches != None:
        return matches.group(1).lower()
    else:
        return None

def starts_with_bold(content : str):
    return content.startswith(forbidden_content)

def add_space(content : str):
    new = hard_space + content
    return new

def sanitize_bold(content : str):
    return add_space(content) if starts_with_bold(content) else content

def create_header(timestamp, sender : str, recip : str=None):
    if recip == None:
        sender_info = f'**{sender}**'
    else:
        sender_info = f'**{sender}** to {recip}'
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
    return sender_info + double_hard_space + timestamp_str + ':\n'

def create_post(message, sender : str, recip : str=None):
    post = sanitize_bold(message.content)
    if sender == None:
        return post
    else:
        header = create_header(message.created_at, sender, recip)
        return header + post

async def repost_message_to_channel(channel, message, sender : str, recip : str=None):
    post = create_post(message, sender, recip)
    files = [await a.to_file() for a in message.attachments]
    await channel.send(post, files=files)

async def repost_message(message, sender : str):
    await repost_message_to_channel(message.channel, message, sender)

async def process_open_message(message, anonymous=False):
    task1 = asyncio.create_task(message.delete())
    current_channel = str(message.channel.name)
    player_id = players.get_player_id(str(message.author.id))
    if anonymous:
        current_poster_id = player_id
        current_poster_display_name = 'Anonymous'
    else:
        handle = handles.get_handle(player_id)
        current_poster_id = handle
        current_poster_display_name = handle
    full_post = channels.record_new_post(current_channel, current_poster_id, message.created_at)
    if full_post:
        task2 = asyncio.create_task(repost_message(message, current_poster_display_name))
    else:
        task2 = asyncio.create_task(repost_message(message, None))
    await task1
    await task2

