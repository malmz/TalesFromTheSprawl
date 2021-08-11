import common_channels
import handles
import players

import re

### Module posting.py
# General message processing (non-command) for system bot.

# Common channels:
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


async def post_message_with_header(channel, content : str, sender_info : str, timestamp):
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
    post = sender_info + ' ' + timestamp_str + ':\n' + content
    await channel.send(post)

async def post_message_with_header_sender_and_recip(channel, content : str, sender : str, recip : str, timestamp):
    sender_info = f'**{sender}** to {recip}'
    await post_message_with_header(channel, content, sender_info, timestamp)

async def post_message_with_header_sender_only(channel, content : str, handle : str, timestamp):
    sender = '**' + handle + '** '
    await post_message_with_header(channel, content, sender, timestamp)

async def repost_message(message, handle):
    if handle == None:
        post = message.content
        await message.channel.send(post)
    else:
        await post_message_with_header_sender_only(message.channel, message.content, handle, message.created_at)

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
        timestamp = ctx.message.created_at
        sender_handle = handles.get_handle(str(ctx.message.author.id))
        response = f'Message sent to {recip_handle}.'
        # Post the same message to recipients inbox and senders outbox
        await post_message_with_header_sender_and_recip(
            inbox_channel,
            content,
            sender_handle,
            recip_handle,
            timestamp
        )
        await post_message_with_header_sender_and_recip(
            outbox_channel,
            content,
            sender_handle,
            recip_handle,
            timestamp
        )
        # Delete the original message with the command
        await ctx.message.delete()
