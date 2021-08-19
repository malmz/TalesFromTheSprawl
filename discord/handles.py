import finances
import players
import actors
import chats
import player_setup
from common import forbidden_content, forbidden_content_print, coin
from custom_types import Handle, HandleTypes

from configobj import ConfigObj
from typing import List
import re

### Module handles.py
# This module tracks and handles state related to handles, e.g. in-game names/accounts that
# players can create.

# 'handles' is the config object holding each user's current handles.
handles = ConfigObj('handles.conf')
active_index = '___active'
last_regular_index = '___last_regular'

# May contain letters, numbers and underscores
# Must start and end with letter or number
# Must be at least two characters (TODO: not necessary, but makes for an easier regex)
alphanumeric_regex = re.compile(f'^[a-zA-Z0-9][a-zA-Z0-9_]*[a-zA-Z0-9]$')
double_underscore = '__'

async def init(clear_all : bool=False):
    if clear_all:
        await clear_all_handles()

async def clear_all_handles():
    for actor_id in handles:
        await clear_all_handles_for_actor(actor_id)

async def clear_all_handles_for_actor(actor_id : str):
    for handle in get_handles_for_actor(actor_id, include_burnt=True):
        await finances.deinit_finances_for_handle(handle, actor_id, record=False)
    del handles[actor_id]
    handles.write()

async def init_handles_for_actor(actor_id : str, first_handle : str=None, overwrite=True):
    if first_handle is None:
        first_handle = actor_id
    if overwrite or actor_id not in handles:
        handles[actor_id] = {}
        handle : Handle = await create_handle(actor_id, first_handle, HandleTypes.Regular)
        switch_to_handle(actor_id, handle)

def is_forbidden_handle(new_handle : str):
    matches = re.search(alphanumeric_regex, new_handle)
    if matches is None:
        return True
    elif double_underscore in new_handle:
        return True
    else:
        return False

async def create_handle(actor_id : str, handle_id : str, handle_type : HandleTypes):
    handle = Handle(handle_id, handle_type = handle_type, actor_id = actor_id)
    if is_forbidden_handle(handle_id):
        handle.handle_type = HandleTypes.Unused
    else:
        store_handle(actor_id, handle)
        finances.init_finances_for_handle(handle)
    return handle

# TODO: we don't really need actor_id as a separate field here
def store_handle(actor_id : str, handle : Handle):
    handles[actor_id][handle.handle_id] = handle.to_string()
    handles.write()

def read_handle(actor_id : str, handle_id : str):
    # Unprotected -- only use for handles that you know exist
    #print(f'{handles[actor_id][handle_id]} at[ {actor_id}][{handle_id}]')
    return Handle.from_string(handles[actor_id][handle_id])

def get_active_handle_id(actor_id : str):
    if actor_id in handles:
        if active_index in handles[actor_id]:
            return handles[actor_id][active_index]
            
def get_active_handle(actor_id : str):
    if actor_id in handles:
        if active_index in handles[actor_id]:
            active_id = handles[actor_id][active_index]
            if active_id in handles[actor_id]:
                return read_handle(actor_id, active_id)

def get_last_regular_id(actor_id : str):
    if actor_id in handles:
        if last_regular_index in handles[actor_id]:
            return handles[actor_id][last_regular_index]

def get_last_regular(actor_id : str):
    if actor_id in handles:
        if last_regular_index in handles[actor_id]:
            last_regular_id = handles[actor_id][last_regular_index]
            if last_regular_id in handles[actor_id]:
                return read_handle(actor_id, last_regular_id)

def is_active_handle_type(handle_type : HandleTypes):
    return handle_type not in [HandleTypes.Burnt, HandleTypes.Unused]

# returns the amount of money (if any) that was transferred away from the burner
async def destroy_burner(guild, actor_id : str, burner : Handle):
    balance = 0
    # If we burn the active handle, we must figure out the new active one
    active : Handle = get_active_handle(actor_id)
    if active.handle_id == burner.handle_id:
        new_active = get_last_regular(actor_id)
        switch_to_handle(actor_id, new_active)
    else:
        new_active = active

    # Rescue any money about to be burned
    balance = finances.get_current_balance(burner)
    if balance > 0:
        await finances.transfer_from_burner(burner, new_active, balance)

    # archive any chats for the burner
    await chats.archive_all_chats_for_handle(burner)

    # Destroy the burner
    burner.handle_type = HandleTypes.Burnt
    store_handle(actor_id, burner)
    await finances.deinit_finances_for_handle(burner, actor_id, record=True)
    return balance

def switch_to_handle(actor_id : str, handle : Handle):
    handles[actor_id][active_index] = handle.handle_id
    if handle.handle_type == HandleTypes.Regular:
        handles[actor_id][last_regular_index] = handle.handle_id
    handles.write()

def get_handles_for_actor(actor_id : str, include_burnt : bool=False, include_npc : bool=True):
    types_list = [HandleTypes.Regular, HandleTypes.Burner]
    if include_burnt:
        types_list.append(HandleTypes.Burnt)
    if include_npc:
        types_list.append(HandleTypes.NPC)
    return get_handles_for_actor_of_types(actor_id, types_list)

def get_handles_for_actor_of_types(actor_id : str, types_list : List[HandleTypes]):
    for handle_id in handles[actor_id]:
        if handle_id != active_index and handle_id != last_regular_index:
            handle = read_handle(actor_id, handle_id)
            if handle.handle_type in types_list:
                yield handle


def get_all_handles():
    for actor_id in handles:
        for handle in get_handles_for_actor(actor_id, include_burnt=True):
            yield handle


def get_handle(handle_name : str):
    handle_id = handle_name.lower()
    for actor_id in handles:
        for handle in get_handles_for_actor(actor_id, include_burnt=True):
            if handle.handle_id == handle_id:
                return handle
    return Handle(handle_id, handle_type=HandleTypes.Unused)


### Async methods, directly related to commands

def current_handle_report(actor_id : str):
    current_handle : Handle = get_active_handle(actor_id)
    if current_handle.handle_type == HandleTypes.Burner:
        response = f'Your current handle is **{current_handle.handle_id}**. It\'s a burner handle – to destroy it, use \".burn {current_handle.handle_id}\". To switch handle, type \".handle <new_name>\".'
    elif current_handle.handle_type == HandleTypes.NPC:
        response = f'Your current handle is **{current_handle.handle_id}**. [OFF: It\'s an NPC handle, so it cannot be directly linked to your other handles, unless they interact with it]'
    elif current_handle.handle_type == HandleTypes.Regular:
        response = f'Your current handle is **{current_handle.handle_id}**. To switch handle, type \".handle <new_name>\".'
    else:
        raise RuntimeError(f'Unexpected handle type of active handle. Dump: {current_handle.to_string()}')
    return response

def switch_to_own_existing_handle(actor_id : str, handle : Handle, expected_type : HandleTypes):
    if handle.handle_type == HandleTypes.Burner:
        if expected_type in [HandleTypes.Regular, HandleTypes.Burner]:
            # We can switch to a burner handle using both .handle and .burner
            response = f'Switched to burner handle **{handle.handle_id}**. Remember to burn it when done, using \".burn {handle.handle_id}\".'
            switch_to_handle(actor_id, handle)
        else:
            response = f'Attempted to switch to {expected_type} handle {handle.handle_id}, but {handle.handle_id} is in fact a burner.'
    elif handle.handle_type == HandleTypes.Burnt:
        # We cannot switch to a burnt handle
        response = f'Error: handle {handle.handle_id} is no longer available.'
    elif handle.handle_type == HandleTypes.Regular:
        if expected_type == HandleTypes.Regular:
            response = f'Switched to handle **{handle.handle_id}**.'
            switch_to_handle(actor_id, handle)
        else:
            # We cannot switch to a non-burner using .burner
            response = f'Handle **{handle.handle_id}** already exists but is not a {expected_type} handle. Use \".handle {handle.handle_id}\" to switch to it.'
    elif handle.handle_type == HandleTypes.NPC:
        response = f'Switched to NPC handle **{handle.handle_id}**.'
        switch_to_handle(actor_id, handle)
    else:
        raise RuntimeError(f'Unexpected handle type of active handle. Dump: {handle.to_string()}')
    return response

async def create_handle_and_switch(actor_id : str, new_handle_id : str, handle_type : HandleTypes):
    handle : Handle = await create_handle(actor_id, new_handle_id, handle_type)
    if handle.handle_type == handle_type and handle.handle_type != HandleTypes.Unused:
        switch_to_handle(actor_id, handle)
        response = await player_setup.player_setup_for_new_handle(handle)
        if response is not None:
            # If something happened in player_setup_for_new_handle(), that report will be enough
            return response
        if handle_type == HandleTypes.Burner:
            # TODO: note about possibly being hacked until destroyed?
            response = (f'Switched to new burner handle **{handle.handle_id}** (created now). '
                + f'To destroy it, use \".burn {handle.handle_id}\".')
        elif handle_type == HandleTypes.NPC:
            response = (f'Switched to new handle **{handle.handle_id}** (created now). '
                + '[OFF: it\'s an NPC handle, meaning it cannot be linked to your regular handles unless they interact with it]')
        else:
            response = f'Switched to new handle **{handle.handle_id}** (created now).'
    else:
        response = (f'Error: cannot create handle {handle.handle_id}. '
            + 'Handles can only contain letters a-z, numbers 0-9, and \_ (underscore). '
            + 'May not start or end with \_, may not have more than one \_ in a row.')
    return response

async def process_handle_command(ctx, new_handle_id : str=None, burner : bool=False, npc : bool=False):
    actor_id = players.get_player_id(str(ctx.message.author.id))
    if new_handle_id == None:
        response = current_handle_report(actor_id)
        if burner:
            response += ' To create a new burner, use \".burner <new_name>\".'
    else:
        existing_handle : Handle = get_handle(new_handle_id)
        handle_type = HandleTypes.Regular
        if burner:
            handle_type = HandleTypes.Burner
        elif npc:
            handle_type = HandleTypes.NPC

        if existing_handle.handle_type != HandleTypes.Unused:
            if existing_handle.actor_id == actor_id:
                response = switch_to_own_existing_handle(actor_id, existing_handle, handle_type)
            elif existing_handle.handle_id != new_handle_id:
                response = f'Error: cannot create handle {new_handle_id} because its internal ID ({existing_handle.handle_id}) clashes with an existing handle.'
            else:
                response = f'Error: the handle {new_handle_id} not available.'
        else:
            response = await create_handle_and_switch(actor_id, new_handle_id, handle_type)
        if existing_handle.handle_id != new_handle_id:
            response += f'\nNote that handles are lowercase only: {new_handle_id} -> **{existing_handle.handle_id}**.'

    return response

async def process_burn_command(ctx, burner_id : str=None):
    if burner_id == None:
        response = 'Error: No burner handle specified. Use \".burn <handle>\"'
    else:
        actor_id = players.get_player_id(str(ctx.message.author.id))
        burner : Handle = get_handle(burner_id)
        if not is_active_handle_type(burner.handle_type):
            response = f'Error: the handle {burner_id} does not exist.'
        elif burner.actor_id != actor_id:
            response = f'Error: you do not have access to {burner_id}.'
        elif burner.handle_type in [HandleTypes.Regular, HandleTypes.NPC]:
            response = f'Error: **{burner_id}** is not a burner handle, cannot be destroyed. To stop using it, simply switch to another handle.'
        elif burner.handle_type == HandleTypes.Burner:
            amount = await destroy_burner(ctx.guild, actor_id, burner)
            current_handle_id = get_active_handle_id(actor_id)
            response = 'Destroyed burner handle **' + burner_id + '**.\n'
            response = response + 'It will not be possible to use again, for anyone. Its previous use cannot be traced to you.\n'
            if amount > 0:
                response = response + f'Your current handle is **{current_handle_id}**; the remaining {coin} {amount} from {burner.handle_id} was transferred there.'
            else:
                response = response + f'Your current handle is **{current_handle_id}**.'
    return response