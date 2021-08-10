from configobj import ConfigObj
import datetime

### channel states
channel_states = ConfigObj('channel_states.conf')

def init_channel(channel : str):
    channel_states[channel] = {}
    set_last_poster(channel, '')
    timestamp = datetime.datetime.today()
    set_last_full_post(channel, timestamp)
    reset_post_counter(channel)

def init_channels():
    init_channel('anon')
    init_channel('open_channel')

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