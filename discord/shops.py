#shops.py

import discord
import asyncio
import simplejson

from configobj import ConfigObj

# Custom imports
import handles
import channels
import players
import actors
import finances
import server

from common import coin, emoji_unavail
from custom_types import Transaction


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

#User reacted with 🛒
#User reacted with 🍿
#User reacted with 🍺
#User reacted with 🥤
#User reacted with 🍸
#User reacted with 🍻
#User reacted with 🍽️

catalogues_dir = 'shops'

shops = ConfigObj(f'shops.conf')

shop_data_index = '__shop_data'
channel_mapping_index = '__channel_mapping'
catalogue_mapping_index = '__catalogue_mapping'

### Module to allow one or more players to run a shop together.
# Having a shop grants:
# - A public storefront, where the menu/catalogue is presented as messages you can react to
# - An "orders" channel, showing what people have ordered recently
# - A "delivery ID" (e.g. table number) for each customer,
#   so that orders can be collected and delivered together
# - An "actor", with the functionality that comes with it (handles, financial reports, chats)
#   albeit restricted to a single handle

### Classes, init and utilities:

class Shop(object):
	def __init__(
		self,
		name : str,
		actor_id : str,
		storefront_channel_id : str,
		order_flow_channel_id : str):
		self.name = name
		self.actor_id = actor_id
		self.shop_id = name.lower() if name is not None else None
		self.storefront_channel_id = storefront_channel_id
		self.order_flow_channel_id = order_flow_channel_id
		self.highest_order = 0

	@staticmethod
	def from_string(string : str):
		obj = Shop(None, None, None, None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)

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

# Used to store a mapping from a storefront msg ID to a product
class CatalogueItemMapping(object):
	def __init__(
		self,
		shop_name : str,
		product_name : str):
		self.shop_name = shop_name
		self.product_name = product_name

	@staticmethod
	def from_string(string : str):
		obj = CatalogueItemMapping(None, None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)

# Used to represent an order (one or more items bought/reserved) by a buyer (handle)
class Order(object):
	def __init__(
		self,
		order_id : str,
		delivery_id : str,
		price_total : int,
		msg_id : str=None,
		time_created=None,
		items_ordered={}):
		self.order_id = order_id
		self.delivery_id = delivery_id
		self.price_total = price_total
		self.msg_id = msg_id
		self.items_ordered = items_ordered
		self.time_created = time_created

	@staticmethod
	def from_string(string : str):
		obj = Order(None, None, None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)


# "Missing" class: ChannelMapping
# Used to store mapping from channel to shop
# No class necessary; just use shop_id : str as the "pointer", indexed by channel ID




async def init(bot, clear_all=False):
	if shop_data_index not in shops:
		shops[shop_data_index] = {}
	if channel_mapping_index not in shops:
		shops[channel_mapping_index] = {}
	if catalogue_mapping_index not in shops:
		shops[catalogue_mapping_index] = {}
	shops.write()
	if clear_all:
		for shop_name in shops[shop_data_index]:
			clear_catalogue(shop_name)
			del shops[shop_data_index][shop_name]
		for channel in shops[channel_mapping_index]:
			del shops[channel_mapping_index][channel]
		for cat_item in shops[catalogue_mapping_index]:
			del shops[catalogue_mapping_index][cat_item]
		shops.write()
		await channels.delete_all_shops(bot)
		# TODO: clear order flow channels

def shop_exists(shop_name : str):
	if shop_name is None:
		return False
	else:
		return shop_name.lower() in shops[shop_data_index]

def store_shop(shop : Shop):
	shops[shop_data_index][shop.shop_id] = shop.to_string()
	shops.write()

def read_shop(shop_name : str):
	shop_id = shop_name.lower()
	if shop_id in shops[shop_data_index]:
		return Shop.from_string(shops[shop_data_index][shop_id])

def record_new_order(shop_name : str):
	shop : Shop = read_shop(shop_name)
	new_order_id = shop.highest_order
	shop.highest_order = new_order_id + 1
	store_shop(shop)
	return new_order_id

def store_storefront_channel_mapping(channel_id : str, shop_name : str):
	shop_id = shop_name.lower()
	shops[channel_mapping_index][channel_id] = shop_id

def read_storefront_channel_mapping(channel_id : str):
	if channel_id in shops[channel_mapping_index]:
		return shops[channel_mapping_index][channel_id]


def store_catalogue_item_mapping(msg_id : str, mapping : CatalogueItemMapping):
	shops[catalogue_mapping_index][msg_id] = mapping.to_string()
	shops.write()

def read_catalogue_item_mapping(msg_id : str):
	if msg_id in shops[catalogue_mapping_index]:
		return CatalogueItemMapping.from_string(shops[catalogue_mapping_index][msg_id])




def get_catalogue(shop_name : str):
	shop_id = shop_name.lower()
	catalogue_file_name = f'{shop_id}.conf'
	return ConfigObj(f'{catalogues_dir}/{catalogue_file_name}')

def get_all_products(shop_name : str):
	catalogue = get_catalogue(shop_name)
	for product_name in catalogue:
		yield read_product_from_cat(catalogue, product_name)


def store_product(shop_name : str, product : Product):
	if shop_exists(shop_name):
		catalogue = get_catalogue(shop_name)
		catalogue[product.name] = product.to_string()
		catalogue.write()

def read_product(shop_name : str, product_name : str):
	if shop_exists(shop_name):
		catalogue = get_catalogue(shop_name)
		return read_product_from_cat(catalogue, product_name)

def read_product_from_cat(catalogue, product_name : str):
	if product_name in catalogue:
		return Product.from_string(catalogue[product_name])

def clear_catalogue(shop_name : str):
	if shop_exists(shop_name):
		catalogue = get_catalogue(shop_name)
		for product in catalogue:
			del catalogue[product]
		catalogue.write()


### Creating a new shop:

async def create_shop(guild, shop_name : str, owner_player_id : str):
	if shop_name is None:
		return 'Error: must give a shop name'
	if owner_player_id is None:
		return f'Error: must give a player id; use \".create_shop {shop_name} <player_id>\"'
	if not players.player_exists(owner_player_id):
		return f'Error: player {owner_player_id} does not exist.'
	if shop_exists(shop_name):
		existing_shop = read_shop(shop_name)
		if existing_shop.name == shop_name:
			return f'Error: the shop {shop_name} already exists.'
		else:
			return (f'Error: cannot create {shop_name} because its internal ID '
				+ f'({shop_name.lower()}) clashes with {existing_shop.name}.)')


	storefront_channel = await channels.create_shop_channel(guild, shop_name)
	storefront_channel_id = str(storefront_channel.shop_id)
	store_storefront_channel_mapping(storefront_channel_id, shop_name)

	order_flow_channel = await channels.create_order_flow_channel(guild, owner_player_id, shop_name)
	order_flow_channel_id = str(order_flow_channel.shop_id)

	# TODO: send welcome message

	shop = Shop(shop_name, owner_player_id, storefront_channel_id, order_flow_channel_id)
	store_shop(shop)
	clear_catalogue(shop.shop_id)
	report = f'Created store {shop.name}, run by {owner_player_id}'
	return report


def get_emoji_for_new_product(symbol : str):
	if symbol is None:
		return emoji_shopping
	elif symbol in product_emojis:
		return product_emojis[symbol]
	else:
		# Hope that the symbol string itself contains an emoji
		return symbol


async def add_product(shop_name : str, product_name : str, description : str, price : int, symbol : str):
	if shop_name is None:
		return 'Error: must give a shop name'
	if product_name is None:
		return f'Error: must give a product name; use \".add_product {shop_name} <product_name>. (Optional: add description, price, and type/symbol)\"'
	if not shop_exists(shop_name):
		return f'Error: shop {shop_name} does not exist'

	emoji = get_emoji_for_new_product(symbol)

	product = Product(
		name=product_name,
		description=description if description is not None else f'Order a {product_name}!',
		price=price,
		emoji=emoji)
	store_product(shop_name, product)
	return (f'Added product {product_name} to {shop_name}.')



### The menu/catalogue: product information messages where players can order by pressing reactions

async def post_catalogue(shop_name : str):
	if shop_name is None:
		return 'Error: must give a shop name'
	if not shop_exists(shop_name):
		return f'Error: shop {shop_name} does not exist'

	shop : Shop = read_shop(shop_name)
	channel = channels.get_discord_channel(shop.storefront_channel_id)

	for product in get_all_products(shop.shop_id):
		if product.available:
			msg_id = await post_catalogue_item_message(channel, product)
			mapping = CatalogueItemMapping(shop.shop_id, product.name)
			store_catalogue_item_mapping(msg_id, mapping)

async def post_catalogue_item(shop_name, product_name):
	if shop_name is None:
		return 'Error: must give a shop name'
	if not shop_exists(shop_name):
		return f'Error: shop {shop_name} does not exist'

	product = read_product(shop_name, product_name)
	if product is None:
		return f'Error: there is no product called {product_name} at {shop_name}'

	shop : Shop = read_shop(shop_name)
	channel = channels.get_discord_channel(shop.storefront_channel_id)

	msg_id = await post_catalogue_item_message(channel, product)
	mapping = CatalogueItemMapping(shop.shop_id, product.name)
	store_catalogue_item_mapping(msg_id, mapping)


async def post_catalogue_item_message(channel, product):
	print(f'{product.to_string()}')
	content = generate_catalogue_item_message(product)
	message = await channel.send(content)
	if product.in_stock:
		await message.add_reaction(product.emoji)
	return str(message.shop_id)


def generate_catalogue_item_message(product):
	if product.in_stock:
		post = f'{product.emoji}   __**{product.name}**__\n'
	else:
		post = f'{emoji_unavail}   __**{product.name}**__ _!!! OUT OF STOCK !!!_\n'
	post += (f'> Price: {coin} **{product.price}**\n'
		+ f'> {product.description}\n'
		)
	return post


### Making an order:

async def order_product(shop_name : str, product_name : str, payer_handle : str, delivery_id : str=None):
	product = read_product(shop_name, product_name)
	if product is None:
		if product_name is None:
			product_name = ''
		if shop_name is None:
			shop_name = ''
		return f'Error: cannot find product {product_name} at shop {shop_name}'
	shop : Shop = read_shop(shop_name)
	shop_id = shop.shop_id


	if payer_handle is None:
		return (f'Error: no payer ID supplied.')
	if delivery_id is None:
		delivery_id = payer_handle

	# TODO: transaction -- but first, fix transaction to be a real class

	order_id = str(record_new_order(shop_id))
	order = Order(order_id, delivery_id, product.price, items_ordered={product.name: 1})
		#msg_id : str,
		#time_created,

	order_flow_channel = channels.get_discord_channel(shop.order_flow_channel_id)
	post = generate_order_message(order)
	await order_flow_channel.send(post)

def generate_order_message(order : Order):
	content = f'**#{order.order_id}** for **{order.delivery_id}**\n'
	for item, amount in order.items_ordered.items():
		content += f'{amount} {item}\n'
	content += f'Total: {coin} {order.price_total} (paid)'
	return content
