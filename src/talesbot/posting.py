import asyncio
import re

import discord

from . import channels, handles, players, server
from .common import forbidden_content, hard_space
from .custom_types import PostTimestamp

### Module posting.py
# General message processing (non-command) for system bot.

# Common channels:
# Mainly implements pseudonymous and anonymous message sending
# by deleting all messages and reposting them with custom
# handles.


class MessageData:
    # Contains message data to be processed
    def __init__(self, content, created_at, attachments=None):
        if attachments is None:
            attachments = []
        self.content = content
        self.created_at = created_at
        self.attachments = attachments

    @staticmethod
    def load_from_discord_message(disc_message: discord.Message):
        return MessageData(
            disc_message.content, disc_message.created_at, disc_message.attachments
        )


double_hard_space = hard_space + hard_space

post_header_regex = re.compile(f"^[*][*](.*)[*][*]{double_hard_space}")


def read_handle_from_post(post: str):
    matches = re.search(post_header_regex, post.lower())
    if matches is not None:
        return matches.group(1).lower()
    else:
        return None


def starts_with_bold(content: str):
    return content.startswith(forbidden_content)


def add_space(content: str):
    return hard_space + content


def sanitize_bold(content: str):
    return add_space(content) if starts_with_bold(content) else content


def create_header(timestamp, sender: str, recip: str | None = None):
    sender_info = f"**{sender}**" if recip is None else f"**{sender}** to {recip}"
    # Manual DST fix:
    post_timestamp = PostTimestamp(timestamp.hour + 2, timestamp.minute)
    timestamp_str = f"({post_timestamp.pretty_print(second=timestamp.second)})"
    return sender_info + double_hard_space + timestamp_str + ":\n"


def create_post(
    msg_data: MessageData,
    sender: str | None,
    recip: str | None = None,
    attachments_supported: bool = True,
):
    post = sanitize_bold(msg_data.content)
    content = post
    if sender is not None:
        header = create_header(msg_data.created_at, sender, recip)
        content = header + content
    if not attachments_supported and len(msg_data.attachments) > 0:
        for attachment in msg_data.attachments:
            content += f"\n*[unavailable file: {attachment.filename}]*"
    return content


# TODO: pass in "full_post : bool" instead of checking sender == None
async def repost_message_to_channel(
    channel, msg_data: MessageData, sender: str | None, recip: str | None = None
):
    post = create_post(msg_data, sender, recip)
    files = [await a.to_file() for a in msg_data.attachments]
    await channel.send(post, files=files)


async def process_open_message(message, anonymous=False):
    tasks = [asyncio.create_task(message.delete())]
    current_channel = str(message.channel.name)
    player_id = players.get_player_id(str(message.author.id))
    if player_id is None:
        # If someone is for some reason not a player (probably an admin or GM not properly initiated):
        # Let the message through, but as "Anonymous"
        anonymous = True
    if anonymous:
        current_poster_id = player_id
        current_poster_display_name = "Anonymous"
    else:
        handle = handles.get_active_handle(player_id)
        if handle is not None:
            current_poster_id = handle.handle_id
            current_poster_display_name = handle.handle_id
        else:
            current_poster_id = player_id
            current_poster_display_name = player_id
    post_time = PostTimestamp.from_datetime(message.created_at, dst_diff=2)
    full_post = channels.record_new_post(current_channel, current_poster_id, post_time)
    mirrored_channels = await server.get_mirrored_channels(message.channel)
    msg_data = MessageData.load_from_discord_message(message)
    for channel in mirrored_channels:
        if full_post:
            tasks.append(
                asyncio.create_task(
                    repost_message_to_channel(
                        channel, msg_data, current_poster_display_name
                    )
                )
            )
        else:
            tasks.append(
                asyncio.create_task(repost_message_to_channel(channel, msg_data, None))
            )
    await asyncio.gather(*tasks)
