import finances
from constants import forbidden_content, forbidden_content_print

from configobj import ConfigObj
import re

### Module handles.py
# This module tracks and handles state related to handles, e.g. in-game names/accounts that
# players can create.

# 'handles' is the config object holding each user's current handles.
handles = ConfigObj('handles.conf')
active_index = '___active'
last_regular_index = '___last_regular'

# TODO: should be able to remove a lot of on-demand initialization now that we init all users


alphanumeric_regex = re.compile(f'^[a-z0-9]*$')

class HandleStatus:
    handle : str = ''
    exists : str = False
    user_id : str = ''
    handle_type : str = ''

def init_handles_for_user(user_id : str, player_id : str = None ):
    handles[user_id] = {}
    if player_id == None:
        first_handle = user_id
    else:
        first_handle = player_id
    create_regular_handle(user_id, first_handle)
    switch_to_handle(user_id, first_handle)

def is_allowed_handle(new_handle : str):
	matches = re.search(alphanumeric_regex, new_handle)
	return matches == None

def create_handle(user_id : str, new_handle : str, burner : bool):
	if is_allowed_handle(new_handle):
		return False
	handles[user_id][new_handle] = 'burner' if burner else 'regular'
	finances.init_finances_for_handle(new_handle)
	handles.write()
	return True

def create_regular_handle(user_id : str, new_handle : str):
	return create_handle(user_id, new_handle, False)

def create_burner_handle(user_id : str, new_burner_handle : str):
	return create_handle(user_id, new_burner_handle, True)

# returns the amount of money (if any) that was transferred away from the burner
async def destroy_burner(guild, user_id : str, burner : str):
	balance = 0
	if burner in handles[user_id]:
	# If we burn the active handle, we must figure out the new active one
		active = handles[user_id][active_index]
		if active == burner:
			new_active = handles[user_id][last_regular_index]
			switch_to_handle(user_id, new_active)
		else:
			new_active = active

		# Rescue any money about to be burned
		balance = finances.get_current_balance(burner)
		if balance > 0:
			await finances.transfer_from_burner(guild, burner, new_active, balance)

		# Delete the burner
		del handles[user_id][burner]
		finances.deinit_finances_for_handle(burner)
	handles.write()
	return balance

def switch_to_handle(user_id : str, handle : str):
    handles[user_id][active_index] = handle
    if handles[user_id][handle] == 'regular':
        handles[user_id][last_regular_index] = handle
    handles.write()

def get_handle(user_id : str):
    if not user_id in handles:
        init_handles_for_user(user_id)
    return handles[user_id][active_index]

def get_handles_for_user(user_id : str):
    for handle in handles[user_id]:
        if handle != active_index and handle != last_regular_index:
            yield handle

def get_all_handles():
    for user_id in handles:
        for handle in handles[user_id]:
            if handle != active_index and handle != last_regular_index:
                yield handle

def handle_exists(handle : str):
    result = HandleStatus()
    for user_id in handles:
        if handle in handles[user_id]:
            return True
    return False

# Sanitize input -- special return on reserved values will protect many commands, including creating
def get_handle_status(handle : str):
    result = HandleStatus()
    for user_id in handles:
        if handle in handles[user_id]:
            result.exists = True
            result.user_id = user_id
            result.handle_type = handles[user_id][handle]
            break
    return result



### Async methods, directly related to commands

def current_handle_report(user_id : str):
    current_handle = get_handle(user_id)
    handle_status : HandleStatus = get_handle_status(current_handle)
    if (handle_status.handle_type == 'burner'):
        response = 'Your current handle is **' + current_handle + '**. It\'s a burner handle – to destroy it, use \".burn ' + current_handle + '\". To switch handle, type \".handle <new_name>\".'
    else:
        response = 'Your current handle is **' + current_handle + '**. To switch handle, type \".handle <new_name>\".'
    return response

def switch_to_own_existing_handle(user_id : str, new_handle : str, handle_status : HandleStatus, new_shall_be_burner):
    if (handle_status.handle_type == 'burner'):
        # We can switch to a burner handle using both .handle and .burner
        response = 'Switched to burner handle **' + new_handle + '**. Remember to burn it when done, using \".burn ' + new_handle + '\".'
        switch_to_handle(user_id, new_handle)
    elif new_shall_be_burner:
        # We cannot switch to a non-burner using .burner
        response = 'Handle **' + new_handle + '** already exists but is not a burner handle. Use \".handle ' + new_handle + '\" to switch to it.'
    else:
        response = 'Switched to handle **' + new_handle + '**.'
        switch_to_handle(user_id, new_handle)
    return response

def create_handle_and_switch(user_id : str, new_handle : str, new_shall_be_burner):
	success = create_handle(user_id, new_handle, new_shall_be_burner)
	if success:
		switch_to_handle(user_id, new_handle)
		if new_shall_be_burner:
			# TODO: note about possibly being hacked until destroyed?
			response = f'Switched to new burner handle **{new_handle}** (created now). To destroy it, use \".burn {new_handle}\".'
		else:
			response = f'Switched to new handle **{new_handle}** (created now).'
	else:
		response = f'Error: cannot create handle {new_handle}. Handles can only contain letters a-z (lowercase) and numbers 0-9.'
	return response

async def process_handle_command(ctx, new_handle : str=None, burner=False):
    user_id = str(ctx.message.author.id)
    if new_handle == None:
        response = current_handle_report(user_id)
        if burner:
        	response += ' To create a new burner, use \".burner <new_name>\".'
    else:
        new_handle_lower = new_handle.lower()
        handle_status : HandleStatus = get_handle_status(new_handle_lower)
        if (handle_status.exists and handle_status.user_id == user_id):
            response = switch_to_own_existing_handle(user_id, new_handle_lower, handle_status, burner)
        elif (handle_status.exists):
            response = f'Error: the handle {new_handle} is currently registered by someone else.'
        else:
            response = create_handle_and_switch(user_id, new_handle_lower, burner)
        if (new_handle_lower != new_handle):
            response += f'\nNote that handles are lowercase only: {new_handle} -> **{new_handle_lower}**.'
    await ctx.send(response)