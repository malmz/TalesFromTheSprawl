import channels
import handles
import actors
from custom_types import Transaction, TransTypes, Handle, HandleTypes
from common import coin, transaction_collector, transaction_collected

from configobj import ConfigObj
import asyncio

### Module finances.py
# This module tracks and handles money and transactions between handles



# TODO: BITCOIN BITCOIN BITCOIN!!!

balance_index = '___balance'
system_fake_handle = '[system]'


# 'finances' holds the money associated with each 
finances = ConfigObj('finances.conf')

def init_finances():
    for handle in handles.get_all_handles():
        if not handle.handle_id in finances and can_have_finances(handle.handle_type):
            init_finances_for_handle(handle)

def init_finances_for_handle(handle : Handle):
    finances[handle.handle_id] = {}
    finances[handle.handle_id][balance_index] = '0'
    finances.write()

async def deinit_finances_for_handle(handle : Handle, actor_id : str, record : bool):
    if handle.handle_id in finances:
        del finances[handle.handle_id]
        finances.write()
    if record:
        await actors.refresh_financial_statement(actor_id)

def get_current_balance(handle : Handle):
    return get_current_balance_handle_id(handle.handle_id)

def get_current_balance_handle_id(handle_id : str):
    return int(finances[handle_id][balance_index])

def set_current_balance(handle : Handle, balance : int):
    set_current_balance_handle_id(handle.handle_id, balance)

def set_current_balance_handle_id(handle_id : str, balance : int):
    finances[handle_id][balance_index] = str(balance)
    finances.write()

async def overwrite_balance(handle : Handle, balance : int):
    old_balance = get_current_balance(handle)
    set_current_balance(handle, balance)
    transaction = Transaction(
        payer=handle.handle_id,
        payer_actor=None,
        recip=system_fake_handle,
        recip_actor=None,
        amount=old_balance,
        cause = TransTypes.Transfer,
        success=True)
    find_transaction_parties(transaction)
    await record_transaction(transaction)

    transaction = Transaction(
        payer=system_fake_handle,
        payer_actor=None,
        recip=handle.handle_id,
        recip_actor=None,
        amount=balance,
        cause = TransTypes.Transfer,
        success=True)
    find_transaction_parties(transaction)
    await record_transaction(transaction)

def can_have_finances(handle_type : HandleTypes):
    return handles.is_active_handle_type(handle_type)

def get_all_handles_balance_report(actor_id : str):
    report = ''

    current_handle : Handle = handles.get_active_handle(actor_id)
    any_npc_found = False
    for handle in handles.get_handles_for_actor_of_types(actor_id, [HandleTypes.NPC]):
        if not any_npc_found:
            any_npc_found = True
            report += '[OFF: Current balance for NPC accounts you control:]\n'
        balance = get_current_balance(handle)
        balance_str = str(balance)
        if handle.handle_id == current_handle.handle_id:
            report = report + f'> [**{handle.handle_id}**: {coin} **{balance_str}**]\n'
        else:
            report = report + f'> [{handle.handle_id}: {coin} **{balance_str}**]\n'

    report += 'Current balance for all your accounts:\n'
    total = 0
    for handle in handles.get_handles_for_actor(actor_id, include_npc=False):
        balance = get_current_balance(handle)
        total += balance
        balance_str = str(balance)
        if handle.handle_id == current_handle.handle_id:
            report = report + f'> **{handle.handle_id}**: {coin} **{balance_str}**'
        else:
            report = report + f'> {handle.handle_id}: {coin} **{balance_str}**'
        if handle.handle_type == HandleTypes.Burner:
            report += '  🔥'
        report += '\n'
    report = report + f'Total: {coin} **{total}**'
    return report

def transfer_funds_if_available(transaction : Transaction):
    avail_at_payer = int(finances[transaction.payer][balance_index])
    if avail_at_payer >= transaction.amount:
        amount_at_recip = get_current_balance_handle_id(transaction.recip)
        set_current_balance_handle_id(transaction.recip, amount_at_recip + transaction.amount)
        set_current_balance_handle_id(transaction.payer, avail_at_payer - transaction.amount)
        transaction.success = True
    else:
        transaction.success = False
    #return transaction

async def transfer_from_burner(burner : Handle, new_active : Handle, amount : int):
    transaction = Transaction(
        payer=burner.handle_id,
        payer_actor=None,
        recip=new_active.handle_id,
        recip_actor=None,
        cause = TransTypes.Burn,
        amount=amount)
    find_transaction_parties(transaction)
    transfer_funds_if_available(transaction)
    await record_transaction(transaction)

async def add_funds(handle : Handle, amount : int):
    if amount == 0:
        return
    previous_balance = int(finances[handle.handle_id][balance_index])
    new_balance = previous_balance + amount
    finances[handle.handle_id][balance_index] = str(new_balance)
    finances.write()
    transaction = Transaction(payer=system_fake_handle, payer_actor=None, recip=handle.handle_id, recip_actor=None, amount=amount)
    find_transaction_parties(transaction)
    await record_transaction(transaction)

async def collect_all_funds(actor_id : str):
    current_handle : Handle = handles.get_active_handle(actor_id)
    if current_handle.handle_type in [HandleTypes.Burnt, HandleTypes.NPC]:
        return f'Error: cannot collect funds to {current_handle.handle_id}. [OFF: it is an NPC account]'
    total = 0
    transaction = Transaction(
        payer=None,
        payer_actor=None,
        recip=transaction_collector,
        recip_actor=None,
        amount=0,
        success=True)
    balance_on_current = 0
    for handle in handles.get_handles_for_actor(actor_id, include_npc=False):
        collected = get_current_balance_handle_id(handle)
        if collected > 0:
            total += collected
            set_current_balance(handle, 0)
            if handle.handle_id == current_handle.handle_id:
                balance_on_current = collected
            else:
                transaction.amount = collected
                transaction.payer = handle.handle_id
                transaction.last_in_sequence = False
                record_transaction(transaction)
    set_current_balance(current_handle, total)
    transaction.amount = total - balance_on_current
    transaction.payer = transaction_collected
    transaction.recip = current_handle
    transaction.last_in_sequence = True
    await record_transaction(transaction)
    return None


# Related to transactions

async def try_to_pay_from_actor(actor_id : str, recip_handle_id : str, amount : int, from_reaction=False):
    # Some input checking has been done here, but we should move it from system_bot.py into here
    handle_payer : Handle = handles.get_active_handle(actor_id)
    transaction = Transaction(
        payer=handle_payer.handle_id,
        payer_actor=handle_payer.actor_id,
        recip=recip_handle_id,
        recip_actor=None,
        cause = TransTypes.Transfer,
        amount=amount)
    # TODO: right now a reaction on e.g. a burnt burner WILL cause error printout every time;
    # "from_reaction" only protects against printout on self-reacts
    find_transaction_parties(transaction)
    if transaction.report is not None:
        return transaction
    else:
        return await try_to_pay(transaction, from_reaction)


# TODO: on second thought, move this into try_to_pay again? We always want to abort and return if this does not succeed
def find_transaction_parties(transaction : Transaction):
    if transaction.payer is None:
        if transaction.payer_actor is None:
            transaction.report = f'Error: attempted transaction without knowing either the handle or the user ID of the payer.'
        else:
            transaction.payer = handles.get_active_handle(transaction.payer_actor).handle_id
            if transaction.payer is None:
                transaction.report = f'Error: attempted transaction for {transaction.payer_actor} but could not find current handle.'
    else:
        if transaction.payer_actor is None and transaction.payer_actor != system_fake_handle:
            payer_handle : Handle = handles.get_handle(transaction.payer)
            if not can_have_finances(payer_handle.handle_type):
                transaction.report = f'Error: attempted transaction from handle {transaction.payer} which does not exist.'
            else:
                transaction.payer_actor = payer_handle.actor_id

    if transaction.recip is None:
        if transaction.recip_actor is None:
            transaction.report = f'Error: attempted transaction without knowing either the handle or the user ID of the recipient.'
        else:
            transaction.recip = handles.get_active_handle(transaction.recip_actor).handle_id
            if transaction.recip is None:
                transaction.report = f'Error: attempted transaction to {transaction.recip_actor} but could not find current handle.'
    else:
        if transaction.recip_actor is None and transaction.recip_actor != system_fake_handle:
            recip_handle : Handle = handles.get_handle(transaction.recip)
            if not can_have_finances(recip_handle.handle_type):
                transaction.report = f'Error: attempted transaction to handle {transaction.recip} which does not exist.'
            else:
                transaction.recip_actor = recip_handle.actor_id

async def try_to_pay(transaction : Transaction, from_reaction : bool=False):
    if transaction.payer == transaction.recip:
        # Cannot transfer to yourself, and cannot transfer to unknown messages
        # On reactions, feedback in cmd_line would just be distracting
        # On a command, we want to give feedback anyway so we might as well say what happened
        if not from_reaction:
            transaction.report = f'Error: cannot transfer funds from account {transaction.recip} to itself.'
        return transaction

    if transaction.amount < 0:
        print(f'Got a negative transaction!')
        # Negative transaction: flip it around
        recip = transaction.payer
        transaction.payer = transaction.recip
        transaction.recip = recip
        recip_actor = transaction.payer_actor
        transaction.payer_actor = transaction.recip_actor
        transaction.recip_actor = recip_actor
        transaction.amount = -transaction.amount


    transfer_funds_if_available(transaction)
    if not transaction.success:
        avail = get_current_balance_handle_id(transaction.payer)
        if from_reaction:
            transaction.report = f'Tried to transfer {coin} **{transaction.amount}** from {transaction.payer} to {transaction.recip} based on your reaction (emoji), but your balance is {avail}.'
        else:
            transaction.report = f'Failed to transfer {coin} **{transaction.amount}** from {transaction.payer} to {transaction.recip}; current balance is {coin} **{avail}**.'
    elif from_reaction:
        # Success; no need for report to cmd_line
        await record_transaction(transaction)
    else:
        if transaction.payer_actor is not None and transaction.payer_actor == transaction.recip_actor:
            transaction.report = f'Successfully transferred {coin} **{transaction.amount}** from {transaction.payer} to **{transaction.recip}**. (Note: you control both accounts.)'
        else:
            transaction.report = f'Successfully transferred {coin} **{transaction.amount}** from {transaction.payer} to **{transaction.recip}**.'
        await record_transaction(transaction)
    return transaction


# Record for transactions:

async def record_transaction(transaction : Transaction):
    if int(transaction.amount) == 0:
        # No need to write anything for 0-transactions, should they occur
        return
    record_payer = generate_record_for_payer(transaction)
    record_recip = generate_record_for_recip(transaction)
    await actors.write_financial_record(transaction, record_payer, record_recip)

def generate_record_for_payer(transaction : Transaction):
    if transaction.payer_actor is None:
        return None
    if transaction.payer_actor == transaction.recip_actor:
        if transaction.cause == TransTypes.Burn:
            # Will be generated for the recipient
            return None
        else:
            return generate_record_self_transfer(transaction)
    if transaction.cause == TransTypes.Transfer:
        return generate_record_payer(transaction)
    if transaction.cause == TransTypes.ChatReact:
        # TODO
        return generate_record_payer(transaction)
    if transaction.cause == TransTypes.Collect:
        return generate_record_collected(transaction)
    if transaction.cause == TransTypes.ShopOrder:
        return generate_record_buyer(transaction)


def generate_record_for_recip(transaction : Transaction):
    if transaction.recip_actor is None:
        return None
    if transaction.payer_actor == transaction.recip_actor:
        if transaction.cause == TransTypes.Burn:
            return generate_record_burner(transaction)
        else:
            # This transaction will be recorded for payer, don't need it twice
            return None
    if transaction.cause == TransTypes.Transfer:
        return generate_record_recip(transaction)
    if transaction.cause == TransTypes.ChatReact:
        # TODO
        return generate_record_recip(transaction)
    if transaction.cause == TransTypes.Collect:
        return generate_record_collector(transaction)
    if transaction.cause == TransTypes.ShopOrder:
        return generate_record_recip_shop(transaction)

# TODO: timestamp for transactions
def generate_record_self_transfer(transaction : Transaction):
    return f'🔁 **{transaction.payer}** --> **{transaction.recip}**: {coin} {transaction.amount}'

def generate_record_payer(transaction : Transaction):
    return f'🟥 **{transaction.payer}** --> {transaction.recip}: {coin} {transaction.amount}'

def generate_record_buyer(transaction : Transaction):
    if transaction.emoji is not None:
        return f'🟥 **{transaction.payer}** --> {transaction.recip}: {coin} {transaction.amount} for {transaction.emoji}'
    else:
        return generate_record_payer(transaction)

def generate_record_recip(transaction : Transaction):
    return f'🟩 {transaction.payer} --> **{transaction.recip}**: {coin} {transaction.amount}'

def generate_record_recip_shop(transaction : Transaction):
    if transaction.emoji is not None:
        return f'🟩 {transaction.payer} --> **{transaction.recip}**: {coin} {transaction.amount} for {transaction.emoji}'
    else:
        return generate_record_recip(transaction)

def generate_record_burner(transaction : Transaction):
    return f'🟩 🔥 ~~{transaction.payer}~~ --> **{transaction.recip}**: {coin} {transaction.amount}'

def generate_record_collected(transaction : Transaction):
    return f'⏬ Collected {coin} {transaction.amount} from **{transaction.payer}**'

def generate_record_collector(transaction : Transaction):
    return f'▶️ --> **{transaction.recip}**: total {coin} {transaction.amount} collected from your other handles.'
