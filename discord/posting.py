import common_channels
import handles
from constants import forbidden_content
import players

import re

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
    matches = re.search(post_header_regex, post)
    if matches != None:
        return matches.group(1)
    else:
        return None

def starts_with_bold(content : str):
    return content.startswith(forbidden_content)

def add_space(content : str):
    new = hard_space + content
    return new

def sanitize_bold(content : str):
    return add_space(content) if starts_with_bold(content) else content

async def post_message_with_header(channel, message, sender_info : str):
    # Manual DST fix:
    timestamp = message.created_at
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
    post = sender_info + double_hard_space + timestamp_str + ':\n' + sanitize_bold(message.content)
    await channel.send(post, files=message.attachments)

async def post_message_with_header_sender_and_recip(channel, message, sender : str, recip : str):
    sender_info = f'**{sender}** to {recip}'
    await post_message_with_header(channel, message, sender_info)

async def post_message_with_header_sender_only(channel, message, handle : str):
    sender = '**' + handle + '**'
    await post_message_with_header(channel, message, sender)

async def post_message_without_header(channel, message):
    await channel.send(sanitize_bold(message.content), files=message.attachments)

async def repost_message(message, handle):
    if handle == None:
        await post_message_without_header(message.channel, message)
    else:
        await post_message_with_header_sender_only(message.channel, message, handle)

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
    full_post = common_channels.new_post(current_channel, current_poster_id, message.created_at)
    if full_post:
        await repost_message(message, current_poster_display_name)
    else:
        await repost_message(message, None)


# Private channels:
# Handle the inbox/outbox dynamic

async def process_email(ctx, recip_handle : str, content : str):
    inbox_channel = players.get_inbox_channel_for_handle(ctx.guild, recip_handle)
    if inbox_channel == None:
        response = f'Error: cannot send message to {recip_handle}. Handle might not exist. Check the spelling.'
        await ctx.send(response)
    else:
        outbox_channel = ctx.message.channel
        sender_handle = handles.get_handle(str(ctx.message.author.id))
        response = f'Message sent to {recip_handle}.'
        # Post the same message to recipients inbox and senders outbox
        await post_message_with_header_sender_and_recip(
            inbox_channel,
            ctx.message,
            sender_handle,
            recip_handle
        )
        await post_message_with_header_sender_and_recip(
            outbox_channel,
            ctx.message,
            sender_handle,
            recip_handle
        )
        # Delete the original message with the command
        await ctx.message.delete()
