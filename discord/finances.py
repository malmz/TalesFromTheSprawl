import channels
import handles
import players
from custom_types import Transaction, ReactionPaymentResult

from configobj import ConfigObj
import asyncio

### Module finances.py
# This module tracks and handles money and transactions between handles



# TODO: BITCOIN BITCOIN BITCOIN!!!

balance_index = '___balance'

# 'finances' holds the money associated with each 
finances = ConfigObj('finances.conf')

def init_finances():
    for handle in handles.get_all_handles():
        if not handle in finances:
            init_finances_for_handle(handle)

def init_finances_for_handle(handle : str):
    finances[handle] = {}
    finances[handle][balance_index] = '0'
    finances.write()

def deinit_finances_for_handle(handle : str):
    del finances[handle]
    finances.write()

def get_current_balance(handle : str):
    return int(finances[handle][balance_index])

def set_current_balance(handle : str, balance : int):
    finances[handle][balance_index] = str(balance)
    finances.write()

def get_all_handles_balance_report(user_id : str):
    current_handle = handles.get_handle(user_id)
    report = ''
    total = 0
    for handle in handles.get_handles_for_user(user_id):
        balance = get_current_balance(handle)
        total += balance
        balance_str = str(balance)
        if handle == current_handle:
            report = report + '> **' + handle + '**: ¥ **' + balance_str + '**\n'
        else:
            report = report + '> ' + handle + ': ¥ **' + balance_str + '**\n'
    report = report + 'Total: ¥ **' + str(total) + '**'
    return report

# TODO: add a transfer method that also sends a report to the financial channel?
def transfer_funds(transaction : Transaction):
    avail_at_payer = int(finances[transaction.payer][balance_index])
    if avail_at_payer >= transaction.amount:
        amount_at_recip = get_current_balance(transaction.recip)
        set_current_balance(transaction.recip, amount_at_recip + transaction.amount)
        set_current_balance(transaction.payer, avail_at_payer - transaction.amount)
        transaction.success = True
    else:
        transaction.success = False
    return transaction

def add_funds(handle : str, amount : int):
    previous_balance = int(finances[handle][balance_index])
    new_balance = previous_balance + amount
    finances[handle][balance_index] = str(new_balance)
    finances.write()

def collect_all_funds(user_id : str):
    current_handle = handles.get_handle(user_id)
    total = 0
    for handle in handles.get_handles_for_user(user_id):
        total += get_current_balance(handle)
        set_current_balance(handle, 0)
    set_current_balance(current_handle, total)


# Related to transactions

# TODO: timestamp for transactions
def generate_record_self_transfer(transaction : Transaction):
    return f'🔁 **{transaction.payer}** --> **{transaction.recip}**: ¥ {transaction.amount}'

def generate_record_payer(transaction : Transaction):
    return f'🟥 **{transaction.payer}** --> {transaction.recip}: ¥ {transaction.amount}'

def generate_record_recip(transaction : Transaction):
    return f'🟩 {transaction.payer} --> **{transaction.recip}**: ¥ {transaction.amount}'

async def try_to_pay(guild, user_id : str, handle_recip : str, amount : int, from_reaction=False):
    handle_payer = handles.get_handle(user_id)
    transaction = Transaction()
    transaction.payer = handle_payer
    transaction.recip = handle_recip
    transaction.amount = amount
    if handle_payer == handle_recip or handle_recip == None:
        # Cannot transfer to yourself, and cannot transfer to unknown messages
        # On reactions, feedback in cmd_line would just be distracting
        # On a command, we want to give feedback anyway so we might as well say what happened
        if not from_reaction:
            transaction.report = f'Error: cannot transfer funds from account {handle_recip} to itself.'
        return transaction
    recip_status : HandleStatus = handles.get_handle_status(handle_recip)
    if not recip_status.exists:
        if from_reaction:
            transaction.report = f'Tried to transfer ¥ **{amount}** based on your reaction (emoji), but recipient {handle_recip} does not exist.'
        else:
            transaction.report = f'Failed to transfer ¥ **{amount}** from {handle_payer} to {handle_recip}; recipient does not exist. Check the spelling; lowercase/UPPERCASE matters.'
    else:
        transaction = transfer_funds(transaction)
        if not transaction.success:
            avail = get_current_balance(handle_payer)
            if from_reaction:
                transaction.report = f'Tried to transfer ¥ **{amount}** from {handle_payer} to {handle_recip} based on your reaction (emoji), but your balance is {amount}.'
            else:
                transaction.report = f'Failed to transfer ¥ **{amount}** from {handle_payer} to {handle_recip}; current balance is ¥ **{avail}**.'
        elif from_reaction:
            # Success; no need for report to cmd_line
            await write_financial_record(guild, transaction)
        else:
            if recip_status.user_id == user_id:
                transaction.report = 'Successfully transferred ¥ **' + str(amount) + '** from ' + handle_payer + ' to **' + handle_recip + '**. (Note: you control both accounts.)'
            else:
                transaction.report = 'Successfully transferred ¥ **' + str(amount) + '** from ' + handle_payer + ' to **' + handle_recip + '**.'
            await write_financial_record(guild, transaction)            
    return transaction

async def write_financial_record(guild, transaction : Transaction):
    payer_channel = players.get_finance_channel_for_handle(guild, transaction.payer)
    recip_channel = players.get_finance_channel_for_handle(guild, transaction.recip)
    if (payer_channel.name == recip_channel.name):
        task1 = asyncio.create_task(payer_channel.send(generate_record_self_transfer(transaction)))
        await task1
    else:
        task1 = asyncio.create_task(payer_channel.send(generate_record_payer(transaction)))
        task2 = asyncio.create_task(recip_channel.send(generate_record_recip(transaction)))
        await task1
        await task2