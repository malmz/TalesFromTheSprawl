
from configobj import ConfigObj


### handles
handles = ConfigObj('handles.conf')
stats = ConfigObj('stats.conf')

class HandleStatus:
    handle = ''
    exists = False
    user_id = 0
    handle_type = ''

def init_handles_for_user(user_id : str):
    handles[user_id] = {}
    #user = await bot.get_user(user_id)
    #create_handle(user_id, user.display_name)
    create_handle(user_id, user_id)
    handles[user_id]['active'] = user.display_name
    handles[user_id]['last_regular'] = user.display_name

def create_handle(user_id : str, new_handle : str):
    handles[user_id][new_handle] = 'regular'
    handles.write()

def create_burner(user_id : str, new_burner_handle : str):
    handles[user_id][new_burner_handle] = 'burner'
    handles.write()

def destroy_burner(user_id : str, burner : str):
    if not user_id in handles:
        handles[user_id] = {}
    if burner in handles[user_id]:
        del handles[user_id][burner]
        if handles[user_id]['active'] == burner:
            switch_to_handle(user_id, handles[user_id]['last_regular'])
    handles.write()

def switch_to_handle(user_id : str, handle : str):
    handles[user_id]['active'] = handle
    if handles[user_id][handle] == 'regular':
        handles[user_id]['last_regular'] = handle
    handles.write()

def get_handle(user_id : str):
    if not user_id in handles:
        init_handles_for_user(user_id)
    return handles[user_id]['active']

def handle_exists(handle : str):
    for user_handles in handles:
        if handle in user_handles:
            return True
    return False

def get_handle_status(handle : str):
    result = HandleStatus()
    for user_id in handles:
        if handle in handles[user_id]:
            result.exists = True
            result.user_id = user_id
            result.handle_type = handles[user_id][handle]
            break
    return result

def init_stats():
	for user_id in handles:
		for handle in handles[user_id]:
			if not handle in stats and handle != 'active' and handle != 'last_regular':
				stats[handle] = {}
				stats[handle]['balance'] = '0'
	stats.write()

def get_current_balance(handle : str):
	return int(stats[handle]['balance'])

def set_current_balance(handle : str, balance : int):
	stats[handle]['balance'] = str(balance)
	stats.write()

def get_all_handles_balance_report(user_id : str):
	current_handle = get_handle(user_id)
	report = ''
	total = 0
	for handle in handles[user_id]:
		if handle != 'active' and handle != 'last_regular':
			balance = get_current_balance(handle)
			total += balance
			balance_str = str(balance)
			if handle == current_handle:
				report = report + '> **' + handle + '**: **¥' + balance_str + '**\n'
			else:
				report = report + '> ' + handle + ': **¥' + balance_str + '**\n'
	report = report + 'Total: **¥' + str(total) + '**'
	return report

def transfer_funds(handle_payer : str, handle_recip : str, amount : int):
	avail_at_payer = int(stats[handle_payer]['balance'])
	if avail_at_payer >= amount:
		amount_at_recip = get_current_balance(handle_recip)
		set_current_balance(handle_recip, amount_at_recip + amount)
		set_current_balance(handle_payer, avail_at_payer - amount)
		return True
	else:
		return False

def add_funds(handle : str, amount : int):
	previous_balance = int(stats[handle]['balance'])
	new_balance = previous_balance + amount
	stats[handle]['balance'] = str(new_balance)
	stats.write()

def collect_all_funds(user_id : str):
	current_handle = get_handle(user_id)
	total = 0
	for handle in handles[user_id]:
		if handle != 'active' and handle != 'last_regular':
			total += get_current_balance(handle)
			set_current_balance(handle, 0)
	set_current_balance(current_handle, total)

