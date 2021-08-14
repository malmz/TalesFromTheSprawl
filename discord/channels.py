from configobj import ConfigObj
import datetime
import discord

from custom_types import PostTimestamp, ChannelIdentifier
import players
import server
import asyncio

### Module common_channels.py
# This module tracks and handles state related to channels

personal_category_name = 'personal_account'
chats_category_name = 'chats'
off_category_name = 'offline'
public_category_name = 'public_network'
shadowlands_category_name = 'shadowlands'

channel_id_index = '___channel_id'
last_poster_index = '___last_poster'
last_full_post_index = '___last_full_post_time'
post_counter_index = '___post_counter'

# Channel state: this is the state of the channel, independent of the handles used in it.

channel_states = ConfigObj('channel_states.conf')


### Utilities:

def clickable_channel_ref(discord_channel):
    return f'<#{discord_channel.id}>'

def is_offline_channel(discord_channel):
    if discord_channel.category == None:
        return True
    else:
        return discord_channel.category.name == off_category_name

def is_public_channel(discord_channel):
    if discord_channel.category == None:
        return False
    else:
        return discord_channel.category.name == public_category_name

def is_chat_channel(discord_channel):
    if discord_channel.category == None:
        return False
    else:
        return discord_channel.category.name == chats_category_name

def is_personal_channel(discord_channel):
    if discord_channel.category == None:
        return False
    else:
        return discord_channel.category.name == personal_category_name

def is_pseudonymous_channel(discord_channel):
    if discord_channel.category == None:
        return False
    else:
        return discord_channel.category.name == public_category_name or discord_channel.category.name == shadowlands_category_name

def is_anonymous_channel(discord_channel):
    return discord_channel.name == 'anon'

def set_channel_id(channel_name : str, ident : ChannelIdentifier):
    channel_states[channel_name][channel_id_index] = ident.to_string()
    channel_states.write()

def get_channel_id(channel_name : str):
    return ChannelIdentifier.from_string(channel_states[channel_name][channel_id_index])

def get_discord_channel_from_name(guild, channel_name : str):
    ident : ChannelIdentifier = get_channel_id(channel_name)
    if ident.discord_channel_id != None:
        return guild.get_channel(ident.discord_channel_id)
    else:
        raise RuntimeError(f'Tried to find discord channel but channel_id missing: {ident.to_string()}')

def get_discord_channel(channel_id : str):
    guild = server.get_guild()
    return guild.get_channel(int(channel_id))


async def delete_discord_channel(channel_id : str):
    guild = server.get_guild()
    channel = guild.get_channel(int(channel_id))
    if channel is not None:
        await channel.delete()

### Common init functions:

def init_discord_channel(discord_channel):
    if discord_channel.type in [discord.ChannelType.category, discord.ChannelType.voice]:
        # No need to do anything for the categories themselves or the voice channels
        return

    if discord_channel.category != None:
        if discord_channel.category.name == personal_category_name:
            init_personal_channel(discord_channel)
        elif discord_channel.category.name == public_category_name:
            init_common_channel(discord_channel)
    else:
        print(f'Will not create channel state for channel {discord_channel.name} which has no category')


def init_channels(bot):
    for elem in channel_states:
        del channel_states[elem]
    channel_states.write()
    for discord_channel in bot.get_all_channels():
        init_discord_channel(discord_channel)

def init_channel_state(discord_channel):
    channel_name = discord_channel.name
    channel_states[channel_name] = {}
    channel_states.write()
    ident = ChannelIdentifier(discord_channel_id=discord_channel.id)
    set_channel_id(discord_channel.name, ident)    

def init_common_channel(discord_channel):
    init_channel_state(discord_channel)
    init_pseudonymous_channel(discord_channel.name)

def init_personal_channel(discord_channel):
    init_channel_state(discord_channel)


### Utilities related to pseudonymous channels, i.e. ones where all messages are reposted using handle

def init_pseudonymous_channel(channel_name : str):
    set_last_poster(channel_name, '')
    timestamp = datetime.datetime.today()
    set_last_full_post(channel_name, timestamp)
    reset_post_counter(channel_name)

def set_last_poster(channel_name : str, poster_id : str):
    channel_states[channel_name][last_poster_index] = poster_id;
    channel_states.write()

def get_last_poster(channel_name : str):
    if not last_poster_index in channel_states[channel_name]:
        return ''
    else:
        return channel_states[channel_name][last_poster_index];

def set_last_post_time(channel_name : str, post_timestamp):
    channel_states[channel_name][last_full_post_index] = post_timestamp.to_string()

def get_last_post_time(channel_name : str):
    return PostTimestamp.from_string(channel_states[channel_name][last_full_post_index])

def set_last_full_post(channel_name : str, timestamp):
    post_time = PostTimestamp(timestamp.hour, timestamp.minute)
    set_last_post_time(channel_name, post_time)
    channel_states.write()

def time_has_passed_since_last_full_post(channel_name : str, timestamp):
    post_time = PostTimestamp(timestamp.hour, timestamp.minute)
    old_time = get_last_post_time(channel_name)
    if post_time != old_time:
        return True
    else:
        return False

def increment_post_counter(channel_name : str):
    count = int(channel_states[channel_name][post_counter_index])
    count += 1
    channel_states[channel_name][post_counter_index] = str(count)
    channel_states.write()
    return count >= 10

def reset_post_counter(channel_name : str):
    channel_states[channel_name][post_counter_index] = str(0)
    channel_states.write()

# Returns True if the new post should be a full post (with sender and timestamp header)
# Returns False if the new post should only include the content itself
def record_new_post(channel_name : str, poster_id : str, timestamp):
    last_poster = get_last_poster(channel_name)
    time_has_passed = time_has_passed_since_last_full_post(channel_name, timestamp)
    counter_has_passed_limit = increment_post_counter(channel_name)

    if last_poster != poster_id or time_has_passed or counter_has_passed_limit:
        set_last_poster(channel_name, poster_id)
        set_last_full_post(channel_name, timestamp)
        reset_post_counter(channel_name)
        return True
    else:
        return False


### Private channels:
# Only visible to some players

async def create_private_channel(guild, overwrites, channel_name : str, category_name : str):
    category = discord.utils.find(lambda cat: cat.name == category_name, guild.channels)
    channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=category)
    init_channel_state(channel)
    return channel


### Personal channels: completely belonging to and owned by one player

cmd_line_base = 'cmd_line_'
inbox_base = 'inbox_'
outbox_base = 'outbox_'
finance_base = 'finance_'
daemon_base = 'daemon_'
chat_hub_base = 'chat_hub_'
# TODO: some sort of dictionary for these, with an enum type

async def delete_all_personal_channels(bot):
    task_list = (asyncio.create_task(c.delete()) for c in get_all_personal_channels(bot))
    await asyncio.gather(*task_list)

def get_all_personal_channels(bot):
    for channel in bot.get_all_channels():
        if is_personal_channel(channel):
            yield channel

async def create_personal_channel(guild, overwrites, channel_name : str):
    return await create_private_channel(guild, overwrites, channel_name, personal_category_name)

def get_cmd_line_name(player_id : str):
    return cmd_line_base + player_id

def is_cmd_line(channel_name : str):
    return cmd_line_base in channel_name

def get_cmd_line_channel(guild, player_id : str):
    channel_name = get_cmd_line_name(player_id)
    return get_discord_channel_from_name(guild, channel_name)


def get_inbox_name(player_id : str):
    return inbox_base + player_id

def is_inbox(channel_name : str):
    return inbox_base in channel_name

def get_inbox_channel(guild, player_id : str):
    channel_name = get_inbox_name(player_id)
    return get_discord_channel_from_name(guild, channel_name)


def get_outbox_name(player_id : str):
    return outbox_base + player_id

def is_outbox(channel_name : str):
    return outbox_base in channel_name


def get_finance_name(player_id : str):
    return finance_base + player_id

def is_finance(channel_name : str):
    return finance_base in channel_name

def get_finance_channel(guild, player_id : str):
    channel_name = get_finance_name(player_id)
    return get_discord_channel_from_name(guild, channel_name)


def get_chat_hub_name(player_id : str):
    return chat_hub_base + player_id

def is_chat_hub(channel_name : str):
    return chat_hub_base in channel_name

def get_chat_hub_channel(guild, player_id : str):
    channel_name = get_chat_hub_name(player_id)
    return get_discord_channel_from_name(guild, channel_name)



### Chat channels:
# These are weird: the "channel" is not the discord channel, but rather a name that can be used to fetch one or more channels
# from the chats.py module

def init_chat_channel(channel_name : str):
    channel_states[channel_name] = {}
    channel_states.write()
    init_pseudonymous_channel(channel_name)
    ident = ChannelIdentifier(chat_channel_name=channel_name)
    set_channel_id(channel_name, ident)

async def create_chat_session_channel(guild, player_id : str, discord_channel_name : str):
    role = players.get_player_role(guild, player_id)
    overwrites = server.generate_overwrites_private_channel(role)
    return await create_private_channel(guild, overwrites, discord_channel_name, chats_category_name)

async def delete_all_chats(bot):
    task_list = (asyncio.create_task(c.delete()) for c in get_all_chat_channels(bot))
    await asyncio.gather(*task_list)

def get_all_chat_channels(bot):
    for channel in bot.get_all_channels():
        if is_chat_channel(channel):
            yield channel



