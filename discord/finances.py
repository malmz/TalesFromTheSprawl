import common_channels
import handles
import players
from custom_types import CompletedTransaction, ReactionPaymentResult

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
def transfer_funds(handle_payer : str, handle_recip : str, amount : int):
    avail_at_payer = int(finances[handle_payer][balance_index])
    transaction = CompletedTransaction()
    transaction.payer = handle_payer
    transaction.recip = handle_recip
    transaction.amount = amount
    if avail_at_payer >= amount:
        amount_at_recip = get_current_balance(handle_recip)
        set_current_balance(handle_recip, amount_at_recip + amount)
        set_current_balance(handle_payer, avail_at_payer - amount)
        #return True
        transaction.success = True
    else:
        transaction.success = False
        transaction.report = 'Error: insufficient funds. Current balance is **' + str(avail) + '**.'
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
def generate_record_self_transfer(transaction : CompletedTransaction):
    return f'🔁 **{transaction.payer}** --> **{transaction.recip}**: ¥ {transaction.amount}'

def generate_record_payer(transaction : CompletedTransaction):
    return f'🟥 **{transaction.payer}** --> {transaction.recip}: ¥ {transaction.amount}'

def generate_record_recip(transaction : CompletedTransaction):
    return f'🟩 {transaction.payer} --> **{transaction.recip}**: ¥ {transaction.amount}'

async def try_to_pay(guild, user_id : str, handle_recip : str, amount : int):
    current_handle = handles.get_handle(user_id)
    if current_handle == handle_recip:
        response = 'Error: cannot transfer funds from account ' + handle_recip + ' to itself.'
        return response
    recip_status : HandleStatus = handles.get_handle_status(handle_recip)
    if not recip_status.exists:
        response = 'Error: recipient \"' + handle_recip + '\" does not exist. Check the spelling; lowercase/UPPERCASE matters.'
    else:
        transaction : CompletedTransaction = transfer_funds(current_handle, handle_recip, amount)
        if not transaction.success:
            avail = get_current_balance(current_handle)
        else:
            if recip_status.user_id == user_id:
                transaction.report = 'Successfully transferred ¥ **' + str(amount) + '** from ' + current_handle + ' to **' + handle_recip + '**. (Note: you control both accounts.)'
            else:
                transaction.report = 'Successfully transferred ¥ **' + str(amount) + '** from ' + current_handle + ' to **' + handle_recip + '**.'
            response = transaction.report
            await write_financial_record(guild, transaction)
    return response

async def try_to_pay_with_reaction(guild, user_id : str, handle_recip : str, amount : int):
    current_handle = handles.get_handle(user_id)
    result = ReactionPaymentResult()
    if current_handle == handle_recip or handle_recip == None:
        # Cannot tip yourself, and cannot tip on unknown messages
        # No action, no report
        result.success = False
        result.report = None
        return result
    recip_status : HandleStatus = handles.get_handle_status(handle_recip)
    if not recip_status.exists:
        result.success = False
        result.report = 'Failed to transfer ¥ **' + str(amount) + '** from ' + current_handle + ' to ' + handle_recip + '; recipient does not exist.'
    else:
        transaction : CompletedTransaction = transfer_funds(current_handle, handle_recip, amount)
        if not transaction.success:
            avail = get_current_balance(current_handle)
            result.report = 'Failed to transfer ¥ **' + str(amount) + '** from ' + current_handle + ' to ' + handle_recip + '; current balance is ¥ **' + str(avail) + '**.'
        else:
            if recip_status.user_id == user_id:
                transaction.report = 'Successfully transferred ¥ **' + str(amount) + '** from ' + current_handle + ' to **' + handle_recip + '**. (Note: you control both accounts.)'
            else:
                transaction.report = 'Successfully transferred ¥ **' + str(amount) + '** from ' + current_handle + ' to **' + handle_recip + '**.'
            result.report = transaction.report
            await write_financial_record(guild, transaction)
    return result

async def write_financial_record(guild, transaction : CompletedTransaction):
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