#shops.py

import discord
import asyncio
import simplejson
import datetime

from configobj import ConfigObj
from typing import List, Tuple
from copy import deepcopy

# Custom imports
import common
import handles
import channels
import players
import actors
import finances
import server

from common import coin, emoji_unavail, shop_role_start, highest_ever_index, emoji_alert
from custom_types import Transaction, TransTypes, ActionResult, Handle, HandleTypes, PostTimestamp


emoji_shopping = '🛒'
emoji_ramen = '🍜'

product_emojis = {
	'shopping' : emoji_shopping,
	'ramen' : emoji_ramen,
	'noodles' : emoji_ramen,
	'beer' : '🍺',
	'water' : '🥤',
	'cocktail' : '🍸',
	'beers' : '🍻',
	'plate' : '🍽️',
	'food' : '🍽️'
}

max_table_number = 10

# Order unchecked: 🟦
# Order checked: ☑️

#User reacted with 🛒
#User reacted with 🍿
#User reacted with 🍺
#User reacted with 🥤
#User reacted with 🍸
#User reacted with 🍻
#User reacted with 🍽️

shops_conf_dir = 'shops'

shops = ConfigObj(f'{shops_conf_dir}/shops.conf')

shop_data_index = '__shop_data'
storefront_channel_map_index = '__storefront_channel_mapping'
orders_channel_map_index = '__order_flow_channel_mapping'

### Module to allow one or more players to run a shop together.
# Having a shop grants:
# - A public storefront, where the menu/catalogue is presented as messages you can react to
# - An "orders" channel, showing what people have ordered recently
# - A "delivery ID" (e.g. table number) for each customer,
#   so that orders can be collected and delivered together
# - An "actor", with the functionality that comes with it (handles, financial reports, chats)
#   albeit restricted to a single handle

### Classes, init and utilities:

# TODO: actor_id and shop_id are always the same; we should remove actor_id from this struct
# (similar to how player_id is also an actor_id)
class Shop(object):
	def __init__(
		self,
		name : str,
		actor_id : str,
		owner_id : str,
		storefront_channel_id : str,
		order_flow_channel_id : str,
		employees : List[str] = []):
		self.name = name
		self.actor_id = actor_id
		self.owner_id = owner_id
		self.shop_id = name.lower() if name is not None else None
		self.storefront_channel_id = storefront_channel_id
		self.order_flow_channel_id = order_flow_channel_id
		self.highest_order = 0
		self.employees = [] if employees == [] else employees
		self.order_collection_limit = 2

	@staticmethod
	def from_string(string : str):
		obj = Shop(None, None, None, None, None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)

class FindShopResult(object):
	def __init__(self, shop : Shop=None, error_report : str=None):
		self.shop = shop
		self.error_report = error_report


class Product(object):
	def __init__(
		self,
		name : str,
		description : str,
		price : int,
		file_name : str=None,
		storefront_msg_id : str=None,
		in_stock : bool=True,
		available : bool=True,
		emoji : str = emoji_shopping):
		self.name = name
		self.product_id = name.lower() if name is not None else None
		self.description = description
		self.price = price
		self.file_name = file_name
		self.storefront_msg_id = storefront_msg_id
		# If available is false, product will not appear at all
		# If in_stock is false, product will appear in menu but with "Out of stock!" and not possible to order
		self.in_stock = in_stock
		self.available = available
		self.emoji = emoji

	@staticmethod
	def from_string(string : str):
		obj = Product(None, None, None, None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)


# Used to represent an order: one or more items bought/reserved that will be delivered together
class Order(object):
	def __init__(
		self,
		order_id : str,
		delivery_id : str,
		price_total : int,
		order_flow_msg_id : str=None,
		time_created : PostTimestamp=None,
		undo_hooks : List[Tuple[str, str]]=[],
		items_ordered={}):
		self.order_id = order_id
		self.delivery_id = delivery_id
		self.price_total = price_total
		self.order_flow_msg_id = order_flow_msg_id
		self.items_ordered = items_ordered
		self.time_created : PostTimestamp = time_created
		self.time_updated : PostTimestamp = time_created
		self.undo_hooks = undo_hooks
		self.updated : bool = False

	@staticmethod
	def from_string(string : str):
		obj = Order(None, None, None)
		loaded_dict = simplejson.loads(string)
		obj.__dict__ = loaded_dict
		obj.time_created : PostTimestamp = PostTimestamp.from_string(loaded_dict['time_created'])
		obj.time_updated : PostTimestamp = PostTimestamp.from_string(loaded_dict['time_updated'])
		return obj

	def to_string(self):
		dict_to_save = deepcopy(self.__dict__)
		dict_to_save['time_created'] = PostTimestamp.to_string(self.time_created)
		dict_to_save['time_updated'] = PostTimestamp.to_string(self.time_updated)
		return simplejson.dumps(dict_to_save)

	def add(self, product_name : str, product_price : str, timestamp : PostTimestamp):
		if product_name in self.items_ordered:
			prev_number = int(self.items_ordered[product_name])
		else:
			prev_number = 0
		new_number = prev_number + 1
		self.items_ordered[product_name] = new_number
		self.time_updated = timestamp
		self.price_total += product_price
		self.updated = True



# "Missing" class: ChannelMapping
# Used to store mapping from channel to shop
# No class necessary; just use shop_id : str as the "pointer", indexed by channel ID




### Init, getters, setters, deleters

# TODO: gm-only function to remove a single shop
# Necessary as fail-safe if we want players to create their own shops

async def init(guild, clear_all=False):
	if clear_all:
		for shop_id in get_all_shop_ids():
			shop : Shop = read_shop(shop_id)
			for player_id in shop.employees:
				players.remove_shop(player_id, shop.shop_id)
			await actors.clear_actor(guild, shop_id)
			clear_catalogue(shop_id)
			clear_delivery_data(shop_id)
			del shops[shop_data_index][shop_id]
		for channel in shops[storefront_channel_map_index]:
			del shops[storefront_channel_map_index][channel]
		for channel in shops[orders_channel_map_index]:
			del shops[orders_channel_map_index][channel]
		shops.write()
		await channels.delete_all_shops()

	if shop_data_index not in shops:
		shops[shop_data_index] = {}
	if highest_ever_index not in shops[shop_data_index] or clear_all:
		shops[shop_data_index][highest_ever_index] = str(shop_role_start)
	if storefront_channel_map_index not in shops:
		shops[storefront_channel_map_index] = {}
	if orders_channel_map_index not in shops:
		shops[orders_channel_map_index] = {}
	shops.write()

	await delete_all_shop_roles(guild, spare_used=not clear_all)

async def delete_all_shop_roles(guild, spare_used : bool):
	task_list = (asyncio.create_task(delete_if_shop_role(r, spare_used)) for r in guild.roles)
	await asyncio.gather(*task_list)

async def delete_if_shop_role(role, spare_used : bool):
	if common.is_shop_role(role.name):
		if not spare_used or len(role.members) == 0:
			print(f'Deleting unused role with name {role.name}')
			await role.delete()


async def reinitialize(user_id : str, shop_name : str):
	result : FindShopResult = find_shop_for_command(user_id, shop_name, must_be_owner=True)
	if result.error_report is not None or result.shop is None:
		return result.error_report
	shop : Shop = result.shop

	order_flow_channel = channels.get_discord_channel(shop.order_flow_channel_id)
	storefront_channel = channels.get_discord_channel(shop.storefront_channel_id)
	await asyncio.gather(
		*[asyncio.create_task(c)
		for c
		in [order_flow_channel.purge(), storefront_channel.purge()]]
		)
	delete_catalogue_item_mappings_for_shop(shop.shop_id)
	await clear_order_data(shop.shop_id)
	shop.highest_order = 1
	store_shop(shop)
	return 'Done.'


def get_next_shop_actor_index():
	prev_highest = int(shops[shop_data_index][highest_ever_index])
	shop_actor_id = str(prev_highest + 1)
	shops[shop_data_index][highest_ever_index] = shop_actor_id
	shops.write()
	return shop_actor_id

def shop_exists(shop_name : str):
	if shop_name is None:
		return False
	else:
		return shop_name.lower() in get_all_shop_ids()

def get_all_shop_ids():
	for shop_id in shops[shop_data_index]:
		if shop_id != highest_ever_index:
			yield shop_id

def store_shop(shop : Shop):
	shops[shop_data_index][shop.shop_id] = shop.to_string()
	shops.write()

def read_shop(shop_name : str):
	shop_id = shop_name.lower()
	if shop_id in shops[shop_data_index]:
		return Shop.from_string(shops[shop_data_index][shop_id])

def record_new_order(shop_name : str):
	shop : Shop = read_shop(shop_name)
	new_order_id = int(shop.highest_order)
	shop.highest_order = new_order_id + 1
	store_shop(shop)
	return str(new_order_id)

def store_storefront_channel_mapping(channel_id : str, shop_name : str):
	shop_id = shop_name.lower()
	shops[storefront_channel_map_index][channel_id] = shop_id

def read_storefront_channel_mapping(channel_id : str):
	if channel_id in shops[storefront_channel_map_index]:
		return shops[storefront_channel_map_index][channel_id]

def store_order_flow_channel_mapping(channel_id : str, shop_name : str):
	shop_id = shop_name.lower()
	shops[orders_channel_map_index][channel_id] = shop_id

def read_order_flow_channel_mapping(channel_id : str):
	if channel_id in shops[orders_channel_map_index]:
		return shops[orders_channel_map_index][channel_id]


catalogue_suffix = '_catalogue.conf'
product_entries_index = '___products'
msg_mapping_index = '___storefront_msg_mappings'

def get_catalogue(shop_name : str):
	shop_id = shop_name.lower()
	catalogue_file_name = f'{shop_id}{catalogue_suffix}'
	return ConfigObj(f'{shops_conf_dir}/{catalogue_file_name}')

def get_all_products(shop_name : str):
	catalogue = get_catalogue(shop_name)
	for product_id in catalogue[product_entries_index]:
		yield read_product_from_cat(catalogue, product_id)

def product_exists(shop_name : str, product_name : str):
	return read_product(shop_name, product_name) is not None


def store_product(shop_name : str, product : Product):
	if shop_exists(shop_name):
		catalogue = get_catalogue(shop_name)
		catalogue[product_entries_index][product.product_id] = product.to_string()
		catalogue.write()

def delete_product(shop_name : str, product_id : str):
	if shop_exists(shop_name):
		catalogue = get_catalogue(shop_name)
		if product_id in catalogue[product_entries_index]:
			del catalogue[product_entries_index][product_id]
			catalogue.write()

def read_product(shop_name : str, product_name : str):
	if shop_exists(shop_name):
		catalogue = get_catalogue(shop_name)
		return read_product_from_cat(catalogue, product_name)

def read_product_from_cat(catalogue, product_name : str):
	product_id = product_name.lower()
	if product_id in catalogue[product_entries_index]:
		return Product.from_string(catalogue[product_entries_index][product_id])


def store_catalogue_item_mapping(shop_name : str, msg_id : str, product_id : str):
	if shop_exists(shop_name):
		catalogue = get_catalogue(shop_name)
		catalogue[msg_mapping_index][msg_id] = product_id
		catalogue.write()

def delete_catalogue_item_mapping(shop_name : str, msg_id : str):
	if shop_exists(shop_name):
		catalogue = get_catalogue(shop_name)
		if msg_id in catalogue[msg_mapping_index]:
			del catalogue[msg_mapping_index][msg_id]
			catalogue.write()

def read_catalogue_item_mapping(shop_name : str, msg_id : str):
	if shop_exists(shop_name):
		catalogue = get_catalogue(shop_name)
		if msg_id in catalogue[msg_mapping_index]:
			return catalogue[msg_mapping_index][msg_id]


def delete_catalogue_item_mappings_for_shop(shop_name : str):
	if shop_exists(shop_name):
		catalogue = get_catalogue(shop_name)
		for msg_id in catalogue[msg_mapping_index]:
			del catalogue[msg_mapping_index][msg_id]
		catalogue.write()


def clear_catalogue(shop_name : str):
	if shop_exists(shop_name):
		catalogue = get_catalogue(shop_name)
		catalogue[product_entries_index] = {}
		catalogue[msg_mapping_index] = {}
		catalogue.write()


# The delivery ID of each player/actor is stored in a simple database

delivery_data_suffix = '_delivery_data.conf'
delivery_ids_index = '___delivery_ids'

def get_delivery_data(shop_name : str):
	shop_id = shop_name.lower()
	delivery_data_file_name = f'{shop_id}{delivery_data_suffix}'
	return ConfigObj(f'{shops_conf_dir}/{delivery_data_file_name}')

def player_has_delivery_id(shop_name : str, player_id : str):
	return get_delivery_id(shop_name, player_id) is not None

def store_delivery_id(shop_name : str, player_id : str, delivery_id : str):
	if shop_exists(shop_name):
		delivery_data = get_delivery_data(shop_name)
		delivery_data[delivery_ids_index][player_id] = delivery_id
		delivery_data.write()

def delete_delivery_id(shop_name : str, player_id : str):
	if shop_exists(shop_name):
		delivery_data = get_delivery_data(shop_name)
		if player_id in delivery_data[delivery_ids_index]:
			del delivery_data[delivery_ids_index][player_id]
			delivery_data.write()

def get_delivery_id(shop_name : str, player_id : str):
	if shop_exists(shop_name):
		delivery_data = get_delivery_data(shop_name)
		return read_delivery_id_from_del_data(delivery_data, player_id)

def read_delivery_id_from_del_data(delivery_data, player_id : str):
	if player_id in delivery_data[delivery_ids_index]:
		return delivery_data[delivery_ids_index][player_id]

def clear_delivery_data(shop_name : str):
	if shop_exists(shop_name):
		delivery_data = get_delivery_data(shop_name)
		delivery_data[delivery_ids_index] = {}
		delivery_data.write()

def delete_delivery_ids_for_actor(actor_id : str):
	for shop_id in get_all_shop_ids():
		delete_delivery_id(shop_id, actor_id)


# The active orders are stored indexed on delivery ID, since there can only be
# one active order for each

order_data_suffix = '_order_data.conf'
active_orders_index = '___active_orders'
locked_orders_index = '___locked_orders'

def get_order_data(shop_name : str):
	shop_id = shop_name.lower()
	order_data_file_name = f'{shop_id}{order_data_suffix}'
	return ConfigObj(f'{shops_conf_dir}/{order_data_file_name}')

def store_active_order(shop_name : str, order : Order):
	if shop_exists(shop_name):
		order_data = get_order_data(shop_name)
		order_data[active_orders_index][order.delivery_id] = order.to_string()
		# TODO: also store the mapping from order_flow_msg_id to this order
		# (needed to process reactions on the orders themselves, to mark as locked or completed)
		order_data.write()

def delete_active_order(shop_name : str, delivery_id : str):
	if shop_exists(shop_name):
		order_data = get_order_data(shop_name)
		if delivery_id in order_data[active_orders_index]:
			del order_data[active_orders_index][delivery_id]
			order_data.write()

def get_active_order(shop_name : str, delivery_id : str):
	if shop_exists(shop_name):
		order_data = get_order_data(shop_name)
		return read_active_order_from_order_data(order_data, delivery_id)

def fetch_all_active_orders(shop_name : str):
	if shop_exists(shop_name):
		order_data = get_order_data(shop_name)
		for delivery_id in order_data[active_orders_index]:
			order = read_active_order_from_order_data(order_data, delivery_id)
			del order_data[active_orders_index][delivery_id]
			order_data.write()
			yield order

def fetch_active_order(shop_name : str, delivery_id : str):
	if shop_exists(shop_name):
		order_data = get_order_data(shop_name)
		return fetch_active_order_from_order_data(order_data, delivery_id)

def read_active_order_from_order_data(order_data, delivery_id : str):
	if delivery_id in order_data[active_orders_index]:
		return Order.from_string(order_data[active_orders_index][delivery_id])

def fetch_active_order_from_order_data(order_data, delivery_id : str):
	if delivery_id in order_data[active_orders_index]:
		order = Order.from_string(order_data[active_orders_index][delivery_id])
		del order_data[active_orders_index][delivery_id]
		order_data.write()
		return order


# The locked orders are stored indexed on order number
def store_locked_order(shop_name : str, order : Order):
	if shop_exists(shop_name):
		order_data = get_order_data(shop_name)
		order_data[locked_orders_index][order.order_id] = order.to_string()
		order_data.write()

def delete_locked_order(shop_name : str, order_id : str):
	if shop_exists(shop_name):
		order_data = get_order_data(shop_name)
		if order_id in order_data[locked_orders_index]:
			del order_data[locked_orders_index][order_id]
			order_data.write()

def get_locked_order(shop_name : str, order_id : str):
	if shop_exists(shop_name):
		order_data = get_order_data(shop_name)
		return read_locked_order_from_order_data(order_data, order_id)

def fetch_locked_order(shop_name : str, order_id : str):
	if shop_exists(shop_name):
		order_data = get_order_data(shop_name)
		return fetch_locked_order_from_order_data(order_data, order_id)

def read_locked_order_from_order_data(order_data, order_id : str):
	if delivery_id in delivery_data[locked_orders_index]:
		return Order.from_string(order_data[locked_orders_index][order_id])

def fetch_locked_order_from_order_data(order_data, order_id : str):
	if delivery_id in delivery_data[locked_orders_index]:
		order = Order.from_string(order_data[locked_orders_index][order_id])
		del order_data[locked_orders_index][order_id]
		return order


async def clear_order_data(shop_name : str):
	if shop_exists(shop_name):
		order_data = get_order_data(shop_name)
		for order in fetch_all_active_orders(shop_name):
			await remove_undo_hooks(order)
		order_data[active_orders_index] = {}
		order_data[locked_orders_index] = {}
		order_data.write()



### Creating a new shop:

async def create_shop(guild, shop_name : str, owner_player_id : str):
	if shop_name is None:
		return 'Error: must give a shop name.'
	if owner_player_id is None:
		return f'Error: must give a player id; use \".create_shop {shop_name} <player_id>\".'
	member = await server.get_member_from_nick(owner_player_id)
	if not players.player_exists(owner_player_id) or member is None:
		return f'Error: player {owner_player_id} does not exist, or does not conform to the server nick scheme.'
	if shop_exists(shop_name):
		existing_shop = read_shop(shop_name)
		if existing_shop.name == shop_name:
			return f'Error: the shop {shop_name} already exists.'
		else:
			return (f'Error: cannot create {shop_name} because its internal ID '
				+ f'({shop_name.lower()}) clashes with {existing_shop.name}.)')

	shop_actor_index = get_next_shop_actor_index()
	actor : actors.Actor = await actors.create_new_actor(guild, actor_index=shop_actor_index, actor_id=shop_name.lower())

	storefront_channel = await channels.create_shop_channel(guild, shop_name)
	storefront_channel_id = str(storefront_channel.id)
	store_storefront_channel_mapping(storefront_channel_id, shop_name)

	role = actors.get_actor_role(guild, actor.actor_id)
	order_flow_channel = await channels.create_order_flow_channel(guild, role, shop_name)
	order_flow_channel_id = str(order_flow_channel.id)
	store_order_flow_channel_mapping(order_flow_channel_id, shop_name)

	# TODO: send welcome message in order_flow_channel
	shop = Shop(shop_name, actor.actor_id, owner_player_id, storefront_channel_id, order_flow_channel_id)
	store_shop(shop)
	clear_catalogue(shop.shop_id)
	clear_delivery_data(shop.shop_id)
	await clear_order_data(shop.shop_id)
	report = f'Created shop {shop.name}, run by {owner_player_id}'

	employment_report = await employ(guild, owner_player_id, shop)
	if employment_report is not None:
		report = report + '\n' + employment_report
	return report



def find_shop_for_command(user_id : str, shop_name : str, must_be_owner : bool=False):
	if user_id is None:
		raise RuntimeError('Tried to find a shop, but the action initiator user_id was not found.')

	result = FindShopResult()
	if shop_name is not None and not shop_exists(shop_name):
		result.error_report = f'Error: there is no shop named {shop_name}.'
		return result

	player_id = players.get_player_id(user_id)
	shops_of_player = players.get_shops(player_id)
	if len(shops_of_player) == 0:
		result.error_report = f'Error: player {player_id} does not have access to any shops'
		return result

	if shop_name is None:
		# If no shop given, assume the player wants us to use their first one
		# If a player works at more than one shop, they will have to use the
		# full syntax of specifying which shop they mean
		shop_name = shops_of_player[0]
		if not shop_exists(shop_name):
			result.error_report = f'Error: there is no shop named {shop_name}.'
			return result
	elif shop_name.lower() not in shops_of_player:
		result.error_report = f'Error: player {player_id} does not have access to shop {shop_name}.'
		return result


	shop : Shop = read_shop(shop_name)
	if must_be_owner and shop.owner_id != player_id:
		result.error_report = f'Error: this action is only permitted for shop owner, which is {shop.owner_id}.'
		return result

	result.shop = shop
	return result



# Employees:

async def employ(guild, player_id : str, shop : Shop):
	member = await server.get_member_from_nick(player_id)
	if not players.player_exists(player_id) or member is None:
		return f'Error: player {player_id} does not exist, or does not conform to the server nick scheme.'

	if player_id in shop.employees:
		return f'Error: player {player_id} already works at {shop.shop_id}.'

	role = actors.get_actor_role(guild, shop.actor_id)
	new_roles = member.roles
	new_roles.append(role)
	await member.edit(roles=new_roles)

	players.add_shop(player_id, shop.actor_id)
	shop.employees.append(player_id)
	store_shop(shop)
	return (f'Added player {player_id} as an employee at {shop.name}. '
		+ 'They now have access to the shop\'s finances, chat and order channels, and can edit the product catalogue.')
	# TODO: ping the new employee?

async def process_employ_command(user_id : str, guild, new_employee_player_id : str, shop_name : str):
	result : FindShopResult = find_shop_for_command(user_id, shop_name)
	if result.error_report is not None or result.shop is None:
		return result.error_report
	shop : Shop = result.shop

	if new_employee_player_id is None:
		return 'Error: must give a player ID'
	if not players.player_exists(new_employee_player_id):
		return f'Error: player {new_employee_player_id} does not exist.'

	return await employ(guild, new_employee_player_id, shop)




## Adding and editing products for a shop


def get_emoji_for_new_product(symbol : str):
	if symbol is None:
		return emoji_shopping
	elif symbol in product_emojis:
		return product_emojis[symbol]
	else:
		# Hope that the symbol string itself contains an emoji
		return symbol


def add_product(user_id : str, product_name : str, description : str, price : int, symbol : str, shop_name : str):
	result : FindShopResult = find_shop_for_command(user_id, shop_name)
	if result.error_report is not None or result.shop is None:
		return result.error_report
	shop : Shop = result.shop

	if product_name is None:
		return f'Error: must give a product name; use \".add_product <product_name> [Optional: description, price, type/symbol]\"'
	if product_exists(shop.shop_id, product_name):
		existing_product = read_product(shop.shop_id, product_name)
		if existing_product.name == product_name:
			return f'Error: the shop {shop.shop_id} already has a product called {product_name}.'
		else:
			return (f'Error: cannot create {product_name} at {shop.shop_id} because its internal ID '
				+ f'({product_name.lower()}) clashes with {existing_product.name}.)')
	if price < 0:
		return f'Error: {product_name} cannot have a negative price.'
	emoji = get_emoji_for_new_product(symbol)

	product = Product(
		name=product_name,
		description=description if description is not None else f'Order a {product_name}!',
		price=price,
		emoji=emoji)
	store_product(shop.shop_id, product)
	return (f'Added product {product_name} to {shop.shop_id}.')


async def remove_product(user_id : str, product_name : str, shop_name : str):
	result : FindShopResult = find_shop_for_command(user_id, shop_name)
	if result.error_report is not None or result.shop is None:
		return result.error_report
	shop : Shop = result.shop

	if product_name is None:
		return f'Error: must give a product name; use \".remove_product <product_name>\"'
	if not product_exists(shop.shop_id, product_name):
		return f'Error: shop {shop.shop_id} has no product called {product_name}.'

	product = read_product(shop.shop_id, product_name)
	# First, remove its listing:
	product.available = False
	channel = channels.get_discord_channel(shop.storefront_channel_id)
	msg_id = await update_catalogue_item_message(shop, channel, product)
	if msg_id is not None:
		raise RuntimeError(f'Error: tried to remove product but it was still published, dump: {product.to_string()}')

	# Then, remove it completely from database:
	delete_product(shop.shop_id, product.product_id)

	return (f'Removed product {product.name} from {shop.shop_id}.')


def edit_product_from_command(user_id : str, product_name : str, key : str, value : str, shop_name : str):
	result : FindShopResult = find_shop_for_command(user_id, shop_name)
	if result.error_report is not None or result.shop is None:
		return result.error_report
	shop : Shop = result.shop
	return edit_product(shop, product_name, key, value)


def edit_product(shop : Shop, product_name : str, key : str, value : str):
	if product_name is None:
		return f'Error: must give a product name; use \".add_product {shop.shop_id} <product_name>. (Optional: add description, price, and type/symbol)\"'
	if key is None:
		return f'Error: must give the property to edit. usage: \".edit_product {shop.shop_id} {product_name} <property> <value>\"'

	key = key.lower()
	if key in ['available', 'in_stock'] and value is None:
		value = 'true'
	if value is None:
		return f'Error: must set the new value of property \"{key}\"'

	product = read_product(shop.shop_id, product_name)
	edited = False

	if key == 'description':
		product.description = value
		edited = True
	elif key in ['available', 'in_stock']:
		if value in ['true', 't', '1']:
			new_value = True
		elif value in ['false', 'f', '0']:
			new_value = False
		else:
			return f'Error: did not understand value \"{value}\" for property \"{key}\"'
		if key == 'available':
			product.available = new_value
		else:
			product.in_stock = new_value
		edited = True
	elif key == 'price':
		try:
			new_price = int(value)
			product.price = new_price
			edited = True
		except ValueError:
			return f'Error: cannot set price to \"{value}\"; must be a number.'
	elif key in ['type', 'symbol', 'emoji']:
		emoji = get_emoji_for_new_product(value)
		edited = emoji != product.emoji
		product.emoji = emoji
	if edited:
		store_product(shop.shop_id, product)
		return 'Done.'
	else:
		return 'Your command resulted in no change.'



### The menu/catalogue: product information messages where players can order by pressing reactions

async def post_catalogue(user_id : str, shop_name : str):
	print(f'Trying to post catalogue')
	result : FindShopResult = find_shop_for_command(user_id, shop_name)
	if result.error_report is not None or result.shop is None:
		return result.error_report
	shop : Shop = result.shop
	print(f'Trying to post catalogue for {shop.to_string()}')

	channel = channels.get_discord_channel(shop.storefront_channel_id)

	for product in get_all_products(shop.shop_id):
		msg_id = await update_catalogue_item_message(shop, channel, product)
		if msg_id is None:
			if product.available:
				raise RuntimeError(f'Error: failed to publish product, dump: {product.to_string()}')
			else:
				# Listing has been removed for non-available item, no issue here
				pass
		else:
			store_catalogue_item_mapping(shop.shop_id, msg_id, product.product_id)
		product.storefront_msg_id = msg_id
		store_product(shop.shop_id, product)
	return 'Done.'

async def post_catalogue_item(user_id : str, product_name : str, shop_name : str):
	result : FindShopResult = find_shop_for_command(user_id, shop_name)
	if result.error_report is not None or result.shop is None:
		return result.error_report
	shop : Shop = result.shop

	product = read_product(shop.shop_id, product_name)
	if product is None:
		return f'Error: there is no product called {product_name} at {shop.shop_id}'

	channel = channels.get_discord_channel(shop.storefront_channel_id)
	msg_id = await update_catalogue_item_message(shop, channel, product)
	if msg_id is None:
		if product.available:
			raise RuntimeError(f'Error: failed to publish product, dump: {product.to_string()}')
		else:
			# Listing has been removed for non-available item, no issue here
			pass
	else:
		store_catalogue_item_mapping(shop.shop_id, msg_id, product.product_id)


async def update_catalogue_item_message(shop : Shop, channel, product : Product):
	if not product.available:
		if product.storefront_msg_id is not None:
			delete_catalogue_item_mapping(shop.shop_id, product.storefront_msg_id)
			try:
				message = await channel.fetch_message(product.storefront_msg_id)
				await message.delete()
			except discord.errors.NotFound:
				# Reference to a message in storefront that is no longer available
				# Doesn't matter since the product should not be available anyway
				pass
		return None

	# Since product is set to available, we need to either post the message or
	# edit the existing one to updated description
	content = generate_catalogue_item_message(product)
	previous_msg = product.storefront_msg_id
	if previous_msg is not None:
		# Instead of sending a new message, update the existing one
		delete_catalogue_item_mapping(shop.shop_id, product.storefront_msg_id)
		try:
			message = await channel.fetch_message(product.storefront_msg_id)
			await asyncio.gather(
				*[asyncio.create_task(c)
				for c
				in [message.clear_reactions(), message.edit(content=content)]]
				)
		except discord.errors.NotFound:
			# Reference to a message in storefront that is no longer available
			# Either due to reinitialize(), or due to being removed by an admin
			previous_msg = None
	if previous_msg is None:
		# There is no previous message to update so we must send a new one
		message = await channel.send(content)

	if product.in_stock:
		await message.add_reaction(product.emoji)
	return str(message.id)

async def edit_catalogue_item_message(channel, product):
	content = generate_catalogue_item_message(product)
	message = await channel.send(content)
	if product.in_stock:
		await message.add_reaction(product.emoji)
	return str(message.id)

def generate_catalogue_item_message(product):
	if product.in_stock:
		post = f'{product.emoji}   __**{product.name}**__\n'
	else:
		post = f'{emoji_unavail}   __**{product.name}**__ _!!! OUT OF STOCK !!!_\n'
	post += (f'> Price: {coin} **{product.price}**\n'
		+ f'> {product.description}\n'
		)
	return post


### Reactions:

### Reaction in storefront: will order a product

async def process_reaction_in_storefront(message, user_id : str, emoji : str):
	result = ActionResult()
	shop_id = read_storefront_channel_mapping(str(message.channel.id))
	if shop_id is None:
		result.report = f'Error: tried to order {emoji} from shop but could not map channel {message.channel.id} to any shop.'
		return result		
	shop : Shop = read_shop(shop_id)
	if shop is None:
		result.report = f'Error: tried to order {emoji} from shop but could not find shop.'
		return result
	product_id : str = read_catalogue_item_mapping(shop.shop_id, str(message.id))
	if product_id is None:
		result.report = f'Error: tried to order {emoji} from {shop.name} but could not map the message to a product.'
		return result
	product : Product = read_product(shop_id, product_id)
	if product is None:
		result.report = f'Error: cannot find product {product_id} at shop {shop.name}.'
		return result
	if product.emoji != emoji:
		# Wrong reaction -- silently ignore it.
		return result

	player_id = players.get_player_id(user_id, expect_to_find=True)
	buyer_handle : Handle = handles.get_active_handle(player_id)

	result = await order_product(shop, product, buyer_handle)
	return result

# TODO: a message in the storefront, where you can react with these to set your table:
# 🍸
# 0️⃣
# 1️⃣
# 2️⃣
# 3️⃣
# 4️⃣
# 5️⃣
# 6️⃣
# 7️⃣
# 8️⃣
# 9️⃣
# 🔟
# 📣





### Making an order:

# TODO: make this a class function
def generate_order_message(order : Order):
	if order.updated:
		content = f'**#{order.order_id}** for **{order.delivery_id}**    {emoji_alert} updated at {order.time_updated.pretty_print()}\n'
	else:
		content = f'**#{order.order_id}** for **{order.delivery_id}**    created at {order.time_created.pretty_print()}\n'
	for item, amount in order.items_ordered.items():
		content += f'> {amount} {item}\n'
	content += f'> Total: {coin} {order.price_total} (paid)'
	return content


async def order_product_from_command(user_id : str, shop_name : str, product_name : str):
	player_id = players.get_player_id(user_id)
	buyer_handle : Handle = handles.get_active_handle(player_id)
	return await order_product_for_buyer(shop_name, product_name, buyer_handle)

async def order_product_for_buyer(shop_name : str, product_name : str, buyer_handle : Handle):
	product = read_product(shop_name, product_name) # This implicitly checks that shop exists
	if product is None:
		print(f'Trying to order {product_name} from {shop_name}, found none')
		if product_name is None:
			return f'Error: no product name given. Use \".order <product_name> <shop_name>\"'
		elif shop_name is None:
			return f'Error: no shop name given. Use \".order {product_name} <shop_name>\"'
	else:
		print(f'Trying to order {product_name} from {shop_name}, found {product.to_string()}')

	if buyer_handle is None:
		return 'Error: no payer ID supplied.'
	if not handles.is_active_handle_type(buyer_handle.handle_type):
		return f'Error: cannot find buyer handle {buyer_handle.handle_id}.'

	shop : Shop = read_shop(shop_name)
	shop_id = shop.shop_id

	result : ActionResult = await order_product(shop, product, buyer_handle)
	return result.report


async def order_product(shop : Shop, product : Product, buyer_handle : Handle):
	result = ActionResult()
	if not product.in_stock:
		return f'Sorry - {shop_name} is all out of {product_name}!'

	delivery_id = get_delivery_id(shop.shop_id, buyer_handle.actor_id)
	if delivery_id is None:
		# No delivery ID set for this player
		delivery_id = buyer_handle.handle_id

	# TODO: use "from_reaction" somehow to ensure not all transaction failures end up in cmd line?
	datetime_timestamp = datetime.datetime.today()
	timestamp = PostTimestamp(datetime_timestamp.hour, datetime_timestamp.minute)
	transaction = Transaction(
		payer=buyer_handle.handle_id,
		payer_actor=buyer_handle.actor_id,
		recip=shop.shop_id,
		recip_actor=shop.actor_id,
		amount=product.price,
		cause=TransTypes.ShopOrder,
		data=product.name,
		timestamp=timestamp)
	transaction.emoji = product.emoji
	#transaction = finances.find_transaction_parties(transaction)
	transaction = await finances.try_to_pay(transaction)
	if not transaction.success:
		result.report = transaction.report
		return result
	# Otherwise, we move on to create the order

	print(f'Final transaction: {transaction.to_string()}')

	await place_order_in_flow(shop, transaction, delivery_id)

	result.report = f'Successfully ordered {product.name} from {shop.name}'
	result.success = True
	return result

async def place_order_in_flow(shop : Shop, purchase : Transaction, delivery_id : str):

	previous_order_updated = False
	order = fetch_active_order(shop.shop_id, delivery_id)
	if order is not None:
		# The previous order will have been deleted from active_orders
		time_diff = PostTimestamp.get_time_diff(order.time_created, purchase.timestamp)
		if time_diff <= shop.order_collection_limit:
			order = await add_to_active_order(shop, order, purchase)
			previous_order_updated = True
		else:
			# Lock the previous order
			await lock_active_order(shop, order, purchase)
			# TODO: also update the order message + any mappings to it
			store_locked_order(shop.shop_id, order)

	if not previous_order_updated:
		order_flow_channel = channels.get_discord_channel(shop.order_flow_channel_id)
		order_id = str(record_new_order(shop.shop_id))
		order = Order(
			order_id,
			delivery_id,
			purchase.amount,
			items_ordered={purchase.data: 1},
			time_created = purchase.timestamp,
			undo_hooks = purchase.get_undo_hooks_list()
			)
		post = generate_order_message(order)
		message = await order_flow_channel.send(post)
		order.order_flow_msg_id = message.id
	store_active_order(shop.shop_id, order)

async def lock_active_order(shop : Shop, order : Order, purchase : Transaction):
	await remove_undo_hooks(order)
	order.undo_hooks = []
	store_locked_order(shop.shop_id, order)

# TODO: make this into an Order class function?
async def remove_undo_hooks(order : Order):
	for (actor_id, msg_id) in order.undo_hooks:
		# These are IDs for messages that could until now be used to undo the transaction
		await actors.lock_tentative_transaction(actor_id, msg_id)

async def add_to_active_order(shop : Shop, order : Order, purchase : Transaction):
	order.add(purchase.data, purchase.amount, purchase.timestamp)
	order_flow_channel = channels.get_discord_channel(shop.order_flow_channel_id)
	order_flow_message = await order_flow_channel.fetch_message(order.order_flow_msg_id)
	content = generate_order_message(order)
	await order_flow_message.delete()
	new_message = await order_flow_channel.send(content)
	# The mapping to the order message itself, for when we need to update it:
	order.order_flow_msg_id = new_message.id
	# The mapping to the messages in each player's respective finance channel, which
	# we need to find when we lock or complete the order, to take away the "undo" possibility
	for t in purchase.get_undo_hooks_list():
		order.undo_hooks.append(t)
	return order


async def attempt_refund(transaction : Transaction, initiator_id : str):
	transaction.success = False
	transaction.cause = TransTypes.ShopRefund
	shop_id = transaction.recip_actor
	shop : Shop = read_shop(shop_id)
	if shop is None:
		transaction.report = f'Error: could not refund purchase becase shop no longer exists.'
		# Unsuccessful -- shop no longer exists!
		return

	datetime_timestamp = datetime.datetime.today()
	timestamp = PostTimestamp(datetime_timestamp.hour, datetime_timestamp.minute)
	time_diff = PostTimestamp.get_time_diff(transaction.timestamp, timestamp)
	# Update timestamp now that we got the info we needed from the old one
	transaction.timestamp=timestamp

	initiated_by_shop = initiator_id == shop_id

	if time_diff > shop.order_collection_limit and not initiated_by_shop:
		# Do not lock in the order automatically -- if the shop wants to refund, they can still do so
		# This means the player can go to the staff and ask for their help, even after trying for themselves first
		transaction.report = (f'Error: could not refund purchase becase too long time has passed (limit: {shop.order_collection_limit} minutes). '
			+ f'If it has not yet been delivered, you can still ask {shop_id} staff to refund it for you.')
		return

	buyer_player_id = transaction.payer_actor
	delivery_id = get_delivery_id(shop_id, buyer_player_id)
	if delivery_id is None:
		delivery_id = handles.get_active_handle_id(buyer_player_id)
		if delivery_id is None:
			if initiated_by_shop:
				transaction.report = (f'Error: could not find order to refund. If the buyer has switched their delivery option '
				+'(e.g. table, address, handle), they need to switch back in order to map the transaction to the order.')
			else:
				transaction.report = (f'Error: could not find order to refund. If you have switched your delivery option '
				+'(e.g. table, address, handle), try switching back to the one you had when you ordered.')
			return

	order = fetch_active_order(shop_id, delivery_id)
	if order is None:
		if initiated_by_shop:
			transaction.report = (f'Error: could not find order to refund. Perhaps it has already been locked in or delivered. '
				+ 'Otherwise, if the buyer has switched their delivery option (e.g. table, address, handle), '
				'they need to switch back in order to map the transaction to the order.')
		else:
			transaction.report = (f'Error: could not find order to refund. If you have switched your delivery option '
				+'(e.g. table, address, handle), try switching back to the one you had when you ordered.')
		return

	product_name = transaction.data
	number_of_product_in_order = 0
	if product_name in order.items_ordered:
		number_of_product_in_order = int(order.items_ordered[product_name])
	if number_of_product_in_order <= 0:
		# This typically means the refund is too late -- perhaps it was clicked right at the same time when staff
		# marked the order as "locked" or "delivered". Both those options should remove the undo option from the
		# buyer's side, though.
		transaction.report = f'Error: could not refund. Order has been delivered, is in preparation, or this item has already been refunded.'
		return

	# attempt to transfer back money
	transaction.amount = -transaction.amount
	# Note: try_to_pay will turn any negative transaction into a positive one first, flipping payer and recip
	await finances.try_to_pay(transaction)

	if not transaction.success:
		# try_to_pay will have put in a good-enough error message
		transaction.report = 'Error: could not refund.\n' + transaction.report
		return

	await execute_refund_in_order_flow(shop, transaction, order)


async def execute_refund_in_order_flow(shop : Shop, refund : Transaction, order : Order):
	# Remove the item from the order:
	product_name = refund.data
	new_number = int(order.items_ordered[product_name]) - 1
	if new_number > 0:
		order.items_ordered[product_name] = new_number
	else:
		del order.items_ordered[product_name]

	order_empty = len(order.items_ordered) == 0

	# Remove the financial record entries for the refunded transaction
	# (also prevents the other party from trying to refund the same purchase a second time)
	undo_hook_message_ids_to_remove = [refund.payer_msg_id, refund.recip_msg_id]
	remaining_undo_hooks = []
	for (actor_id, msg_id) in order.undo_hooks:
		if msg_id in undo_hook_message_ids_to_remove:
			await actors.remove_tentative_transaction(actor_id, msg_id)
		elif order_empty:
			# If the order is empty, we don't expect any other undo hooks,
			# but we may as well remove the "undo" option if any are lingering
			await actors.lock_tentative_transaction(actor_id, msg_id)
		else:
			remaining_undo_hooks.append((actor_id, msg_id))
	order.undo_hooks = remaining_undo_hooks

	try:
		order_flow_channel = channels.get_discord_channel(shop.order_flow_channel_id)
	except discord.errors.NotFound:
		refund.success = False
		refund.report = f'Error: refund performed but {shop.name} database is corrupt -- order status may be shown wrong.'
		return
		# Either the channel or the message is missing. 
	try:
		order_flow_message = await order_flow_channel.fetch_message(order.order_flow_msg_id)
	except discord.errors.NotFound:
		if not order_empty:
			refund.success = False
			refund.report = f'Error: refund performed but {shop.name} database is corrupt -- order status may be shown wrong.'
			# Post a new message -- there may be an old one that we have lost track of, but this is better than nothing
			content = generate_order_message(order)
			message = await order_flow_channel.send(content)
			order.order_flow_msg_id = message.id
			store_active_order(shop.shop_id, order)

	if order_empty:
		# There is nothing left, so we shall remove the order
		await order_flow_message.delete()
		alert = (f'Order #{order.order_id} for {order.delivery_id} has been cancelled. '
			+ f'The last item that was refunded was 1 {refund.data} {refund.emoji}.')
		await order_flow_channel.send(alert, delete_after=10)
	else:
		order.price_total -= refund.amount
		content = generate_order_message(order)
		await order_flow_message.edit(content=content)
		store_active_order(shop.shop_id, order)





### Delivery IDs -- where a player's order is to be delivered e.g. a table number

def check_delivery_id_input(delivery_id :str, shop_name : str):
	if delivery_id is None:
		return 'Error: must give a delivery ID.'
	if shop_name is None:
		return 'Error: must give a shop name.'
	if not shop_exists(shop_name):
		return f'Error: There is no shop called {shop_name}.'

def set_delivery_id_from_command(user_id : str, delivery_id :str, shop_name : str):
	report = check_delivery_id_input(delivery_id, shop_name)
	if report is not None:
		return report
	player_id = players.get_player_id(user_id, expect_to_find=True)
	store_delivery_id(shop_name, player_id, delivery_id)	
	return f'Done. All orders made by {player_id} (using any handle!) at {shop_name} will be delivered to {delivery_id}.'



# A special version of set_delivery_id 
def set_delivery_table_from_command(user_id : str, option :str, shop_name : str):
	report = check_delivery_id_input(option, shop_name)
	if report is not None:
		return report

	player_id = players.get_player_id(user_id, expect_to_find=True)
	if option == 'bar':
		delivery_id = 'the bar'
		delivery_str = f'served at the **bar**'
	elif option == 'call':
		# Call out the order for their current handle
		handle_id = handles.get_active_handle_id(player_id)
		if handle_id is None:
			return f'Error: Tried to set delivery option to \"call out my name\", but could not determine your current handle!'
		delivery_id = f'{handle_id} (call out)'
		delivery_str = f'called out to **{handle_id}**'
	else:
		try:
			table_number = int(option)
			if table_number < 0 or table_number > max_table_number:
				return f'Error: there is no table {option} at {shop_name}'
			delivery_id = f'Table {table_number}'
			delivery_str = f'delivered to **{delivery_id}**'
		except ValueError:
			return f'Error: \"{option}\" is not a valid table number (0–{max_table_number}) or delivery option.'

	store_delivery_id(shop_name, player_id, delivery_id)
	return f'Done. All orders made by {player_id} (using any handle!) at {shop_name} will be {delivery_str}.'
