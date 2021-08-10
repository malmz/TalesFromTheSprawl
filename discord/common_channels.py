from configobj import ConfigObj
import datetime

### Module channels.py
# This module tracks and handles state related to channels


# Channel state: this is the state of a channel, independent of its users.
# Mostly relevant for common channels, not personal ones.

channel_states = ConfigObj('channel_states.conf')

def init_channel(channel):
    channel_name = channel.name
    channel_states[channel_name] = {}
    set_last_poster(channel_name, '')
    timestamp = datetime.datetime.today()
    set_last_full_post(channel_name, timestamp)
    reset_post_counter(channel_name)
    set_channel_id(channel)

def init_channels(bot):
    for channel in bot.get_all_channels():
        init_channel(channel)

def set_channel_id(channel):
    channel_states[channel.name]['id'] = channel.id

def get_channel_id(channel_name : str):
    return channel_states[channel.name]['id']

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

