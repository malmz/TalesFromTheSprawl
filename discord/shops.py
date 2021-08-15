#shops.py

import discord
import asyncio
import simplejson

from configobj import ConfigObj

# Custom imports
import handles
import channels
import players
import finances
import server



shops = ConfigObj(f'shops.conf')

### Module to set certain player to have a shop.
# Having a shop grants:
# - A public storefront, where the "meny" is presented as messages you can react to
# - An "orders" channel, showing what people have ordered recently
# - A "delivery ID" (e.g. table number) for each customer,
#   so that orders can be collected and delivered together

### Classes, init and utilities:

class Shop(object):
	def __init__(self, shop_name : str, player_id : str):
		self.shop_name = shop_name
		self.player_id = player_id
		self.shop_id = shop_name.lower() if shop_name is not None else None

	@staticmethod
	def from_string(string : str):
		obj = Shop(None, None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)


def init(clear_all=False):
	if clear_all:
		for shop_name in shops:
			del shops[shop_name]
		shops.write()


def shop_exists(shop_name : str):
	return shop_name.lower() in shops

def store_shop(shop : Shop):
	shops[shop.shop_id] = shop.to_string()
	shops.write()

def read_shop(shop_name : str):
	shop_id = shop_name.lower()
	if shop_id in shops:
		return Shop.from_string(shops[shop_id])



### Creating a new shop:

async def create_shop(guild, shop_name : str, player_id : str):
	if shop_name is None:
		return 'Error: must give a shop name'
	if player_id is None:
		return f'Error: must give a player id; use \".create_shop {shop_name} <player_id>\"'
	if shop_exists(shop_name):
		existing_shop = read_shop(shop_name)
		if existing_shop.shop_name == shop_name:
			return f'Error: the shop {shop_name} already exists.'
		else:
			return (f'Error: cannot create {shop_name} becauseits internal ID '
				+ f'({shop_name.lower()}) clashes with {existing_shop.shop_name}.)')
		

	shop = Shop(shop_name, player_id)
	store_shop(shop)


	# TODO: create storefront channel, give public access

	# TODO: create internal order flow channel, give owner access

	report = f'Created store {shop_name}, run by {player_id}'
	return report




