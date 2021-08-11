from configobj import ConfigObj

import datetime
import discord

### Module common_channels.py
# This module tracks and handles state related to channels

personal_category_name = 'personal_account'
off_category_name = 'offline'
public_category_name = 'public_network'
shadowlands_category_name = 'shadowlands'

# Channel state: this is the state of the channel, independent of the handles used in it.

channel_states = ConfigObj('channel_states.conf')

def is_offline_channel(channel):
    if channel.category == None:
        return True
    else:
        return channel.category.name == off_category_name

def is_public_channel(channel):
    if channel.category == None:
        return False
    else:
        return channel.category.name == public_category_name

def is_pseudonymous_channel(channel):
    if channel.category == None:
        return False
    else:
        return channel.category.name == public_category_name or channel.category.name == shadowlands_category_name


def init_channel(channel):
    if channel.type == discord.ChannelType.category or channel.type == discord.ChannelType.voice:
        # No need to do anything for the categories themselves or the voice channels
        return

    if channel.category != None:
        if channel.category.name == personal_category_name:
            init_personal_channel(channel)
        elif not channel.category.name == off_category_name:
            init_common_channel(channel)
        else:
            print(f'Will not create channel state for channel {channel.name} in category {channel.category.name}')
    else:
        print(f'Will not create channel state for channel {channel.name} which has no category')

def init_channels(bot):
    for channel in bot.get_all_channels():
        init_channel(channel)

# Common channels:

def init_common_channel(channel):
    channel_name = channel.name
    channel_states[channel_name] = {}
    set_channel_id(channel)
    set_last_poster(channel_name, '')
    timestamp = datetime.datetime.today()
    set_last_full_post(channel_name, timestamp)
    reset_post_counter(channel_name)

def set_channel_id(channel):
    channel_states[channel.name]['id'] = channel.id
    channel_states.write()

def get_channel_id(channel_name : str):
    return channel_states[channel_name]['id']

def is_anonymous_channel(channel):
    return channel.name == 'anon'

def set_last_poster(channel : str, poster_id : str):
    if not channel in channel_states:
        init_channel(channel)
    channel_states[channel]['last_poster'] = poster_id;
    channel_states.write()

def get_last_poster(channel : str):
    if not channel in channel_states:
        return ''
    if not 'last_poster' in channel_states[channel]:
        return ''
    else:
        return channel_states[channel]['last_poster'];

def set_last_full_post(channel : str, timestamp):
    if not channel in channel_states:
        init_channel(channel);
    channel_states[channel]['last_poster_info_hour'] = str(timestamp.hour)
    channel_states[channel]['last_poster_info_minute'] = str(timestamp.minute)
    channel_states.write()

def time_has_passed_since_last_full_post(channel, timestamp):
    if not channel in channel_states:
        init_channel(channel)
        return True
    hour = str(timestamp.hour)
    minute = str(timestamp.minute)
    old_hour = channel_states[channel]['last_poster_info_hour']
    old_minute = channel_states[channel]['last_poster_info_minute']
    if minute != old_minute or hour != old_hour:
        return True
    else:
        return False

def increment_post_counter(channel):
    if not channel in channel_states:
        init_channel(channel)
    count = int(channel_states[channel]['post_counter'])
    count += 1
    channel_states[channel]['post_counter'] = str(count)
    channel_states.write()
    return count >= 10

def reset_post_counter(channel):
    channel_states[channel]['post_counter'] = str(0)
    channel_states.write()

def new_post(channel : str, poster_id : str, timestamp):
    last_poster = get_last_poster(channel)
    time_has_passed = time_has_passed_since_last_full_post(channel, timestamp)
    counter_has_passed_limit = increment_post_counter(channel)

    if last_poster != poster_id or time_has_passed or counter_has_passed_limit:
        set_last_poster(channel, poster_id)
        set_last_full_post(channel, timestamp)
        reset_post_counter(channel)
        return True
    else:
        return False


# Personal channels:

cmd_line_base = 'cmd_line_'
inbox_base = 'inbox_'
outbox_base = 'outbox_'
finance_base = 'finance_'
daemon_base = 'daemon_'
private_base = 'private_chats_'
# TODO: some sort of dictionary for these, with an enum type

async def create_personal_channel(member, overwrites, channel_name):
    category_personal = discord.utils.find(lambda cat: cat.name == personal_category_name, member.guild.channels)
    channel = await member.guild.create_text_channel(channel_name, overwrites=overwrites, category=category_personal)
    init_personal_channel(channel)
    return channel

def init_personal_channel(channel):
    channel_states[channel.name] = {}
    set_channel_id(channel)
    channel_states.write()

def get_channel_from_name(guild, channel_name : str):
    channel_id = get_channel_id(channel_name)
    return guild.get_channel(channel_id)


def get_cmd_line_name(player_id : str):
    return cmd_line_base + player_id

def is_cmd_line(channel_name : str):
    return cmd_line_base in channel_name

def get_cmd_line_channel(guild, player_id : str):
    channel_name = get_cmd_line_name(player_id)
    return get_channel_from_name(guild, channel_name)


def get_inbox_name(player_id : str):
    return inbox_base + player_id

def is_inbox(channel_name : str):
    return inbox_base in channel_name

def get_inbox_channel(guild, player_id : str):
    channel_name = get_inbox_name(player_id)
    return get_channel_from_name(guild, channel_name)


def get_outbox_name(player_id : str):
    return outbox_base + player_id

def is_outbox(channel_name : str):
    return outbox_base in channel_name


def get_finance_name(player_id : str):
    return finance_base + player_id

def is_inbox(channel_name : str):
    return finance_base in channel_name

def get_inbox_channel(guild, player_id : str):
    channel_name = get_finance_name(player_id)
    return get_channel_from_name(guild, channel_name)



