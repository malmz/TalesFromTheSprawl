
from configobj import ConfigObj

### Module handles.py
# This module tracks and handles state related to handles, e.g. in-game names/accounts that
# players can create.

# 'handles' is the config object holding each user's current handles.
handles = ConfigObj('handles.conf')
# 'stats' holds extra information associated with each handle, unrelated to who owns it.
# The main stat (currently the only one implemented) is 'balance', tracking the account's money.
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
    init_stats_for_handle(new_handle)
    handles.write()

def create_burner(user_id : str, new_burner_handle : str):
    handles[user_id][new_burner_handle] = 'burner'
    init_stats_for_handle(new_burner_handle)
    handles.write()

def destroy_burner(user_id : str, burner : str):
    if not user_id in handles:
        handles[user_id] = {}
    if burner in handles[user_id]:
        del handles[user_id][burner]
        deinit_stats_for_handle(burner)
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
    for user_id in handles:
        if handle in handles[user_id]:
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
				init_stats_for_handle(handle)

def init_stats_for_handle(handle : str):
	stats[handle] = {}
	stats[handle]['balance'] = '0'
	stats.write()

def deinit_stats_for_handle(handle : str):
	del stats[handle]
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
				report = report + '> **' + handle + '**: ¥ **' + balance_str + '**\n'
			else:
				report = report + '> ' + handle + ': ¥ **' + balance_str + '**\n'
	report = report + 'Total: ¥ **' + str(total) + '**'
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






### Async methods, directly related to commands

def try_switch_to_none_handle(user_id : str):
    current_handle = get_handle(user_id)
    handle_status : HandleStatus = get_handle_status(current_handle)
    if (handle_status.handle_type == 'burner'):
        response = 'Your current handle is **' + current_handle + '**. It\'s a burner handle – to destroy it, use \".burn ' + current_handle + '\". To switch handle, type \".handle <new_name>\" in #command_line.'
    else:
        response = 'Your current handle is **' + current_handle + '**. To switch handle, type \".handle <new_name>\" in #command_line.'
    return response

def switch_to_own_existing_handle(user_id : str, new_handle : str, handle_status : HandleStatus, new_shall_be_burner):
    if (handle_status.handle_type == 'burner'):
        # We can switch to a burner handle using both .handle and .burner
        response = 'Switched to burner handle **' + new_handle + '**. Remember to burn it when done, using \".burn ' + new_handle + '\" in #command_line.'
        switch_to_handle(user_id, new_handle)
    elif new_shall_be_burner:
        # We cannot switch to a non-burner using .burner
        response = 'Handle **' + new_handle + '** already exists but is not a burner handle. Use \".handle ' + new_handle + '\" to switch to it.'
    else:
        response = 'Switched to handle **' + new_handle + '**.'
        switch_to_handle(user_id, new_handle)
    return response

def create_handle_and_switch(user_id : str, new_handle : str, new_shall_be_burner):
    if new_shall_be_burner:
        # TODO: note about possibly being hacked until destroyed?
        response = 'Switched to new burner handle **' + new_handle + '** (created now). To destroy it, use \".burn ' + new_handle + '\" in #command_line.'
        create_burner(user_id, new_handle)
    else:
        response = 'Switched to new handle **' + new_handle + '** (created now).'
        create_handle(user_id, new_handle)
    switch_to_handle(user_id, new_handle)
    return response


def try_to_pay(user_id : str, handle_recip : str, amount : int):
    current_handle = get_handle(user_id)
    if current_handle == handle_recip:
        response = 'Error: cannot transfer funds from account ' + handle_recip + ' to itself.'
        return response
    recip_status : HandleStatus = get_handle_status(handle_recip)
    if not recip_status.exists:
        response = 'Error: recipient \"' + handle_recip + '\" does not exist. Check the spelling; lowercase/UPPERCASE matters.'
    else:
        success = transfer_funds(current_handle, handle_recip, amount)
        if not success:
            avail = get_current_balance(current_handle)
            response = 'Error: insufficient funds. Current balance is **' + str(avail) + '**.'
        elif recip_status.user_id == user_id:
            response = 'Successfully transferred ¥ **' + str(amount) + '** from ' + current_handle + ' to **' + handle_recip + '**. (Note: you control both accounts.)'
        else:
            response = 'Successfully transferred ¥ **' + str(amount) + '** from ' + current_handle + ' to **' + handle_recip + '**.'
    return response
