#stores.py

import discord
import asyncio

from configobj import ConfigObj

# Custom imports
import handles
import channels
import players
import finances
import server
import stores



### Module to set certain player to have a store.
# Being a store grants:
# - A public storefront, where the "meny" is presented as messages you can react to
# - An "orders" channel, showing what people have ordered recently
# - A "delivery ID" (e.g. table number) for each customer,
#   so that orders can be collected and delivered together


async def create_store(guild, store_name : str, player_id : str):
	if store_name is None:
		return 'Error: must give a store name'
	if player_id is None:
		return f'Error: must give a player id; use \".create_store {store_name} <player_id>\"'

	report = f'Creating store {store_name}, run by {player_id}'
	return report