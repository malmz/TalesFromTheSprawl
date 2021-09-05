import discord
import asyncio
import simplejson
from configobj import ConfigObj
from enum import Enum
from typing import List

import players
import handles
import channels
import server
import finances
import groups
import shops
import actors
from shops import Shop
from custom_types import Handle, HandleTypes, Actor, ActionResult
from common import coin


# Known_handles is meant to be read-only during the event
# It can be edited manually
known_handles = ConfigObj('known_handles.conf')

class PlayerSetupInfo(object):
	def __init__(
		self,
		handle_id : str):
		self.handle_id = handle_id
		self.other_handles = [('__example_handle1', 0), ('__example_handle2', 0)]
		self.npc_handles = [('__example_npc1', 0), ('__example_npc1', 0)]
		self.burners = [('__example_burner1', 0), ('__example_burner1', 0)]
		self.groups = ['__example_group1', '__example_group2']
		self.shops_owner = ['__example_shop1']
		self.shops_employee = ['__example_shop1']
		self.starting_money = 10

	@staticmethod
	def from_string(string : str):
		obj = PlayerSetupInfo(None)
		obj.__dict__ = simplejson.loads(string)
		return obj

	def to_string(self):
		return simplejson.dumps(self.__dict__)

double_underscore = '__'

def remove_examples(entries : List[str]):
	for entry in entries:
		if double_underscore not in entry:
			yield entry

def add_known_handle(handle_id : str):
	if handle_id not in known_handles:
		known_handles[handle_id] = PlayerSetupInfo(handle_id).to_string()
		known_handles.write()
	else:
		print(f'Trying to edit player setup info for a handle that is already in the database. Please edit the file manually instead.')

def read_player_setup_info(handle_id : str):
	if handle_id in known_handles:
		return PlayerSetupInfo.from_string(known_handles[handle_id])


def reload_known_handles():
	global known_handles
	known_handles = ConfigObj('known_handles.conf')


async def player_setup_for_new_handle(handle : Handle):
	info = read_player_setup_info(handle.handle_id)
	reload_known_handles()
	if info is None:
		return None
	report = f'Loading known data for **{handle.handle_id}**...\n\n'
	if finances.can_have_finances(handle.handle_type):
		await finances.add_funds(handle, int(info.starting_money))
		report += f'Initial balance of **{handle.handle_id}**: {coin} **{info.starting_money}**\n\n'

	report += await setup_alternate_handles(handle, info.other_handles, HandleTypes.Regular)
	report += await setup_alternate_handles(handle, info.burners, HandleTypes.Burner)
	report += await setup_alternate_handles(handle, info.npc_handles, HandleTypes.NPC)

	report += await setup_groups(handle, info.groups)

	report += await setup_owned_shops(handle, info.shops_owner)
	report += await setup_employed_shops(handle, info.shops_employee)

	report += f'All data loaded. Welcome, **{handle.handle_id}**.'
	return report


async def setup_alternate_handles(main_handle, aliases, alias_type : HandleTypes):
	report = ''
	any_found = False
	for (other_handle_id, amount) in aliases:
		# TODO: check if handle already exists and throw error
		other_handle = await handles.create_handle(main_handle.actor_id, other_handle_id, alias_type)
		if other_handle.handle_type != HandleTypes.Unused:
			report += get_connected_alias_report(other_handle_id, alias_type, int(amount))
			await finances.add_funds(other_handle, int(amount))
			any_found = True
	if any_found:
		report += get_all_connected_aliases_of_type_report(alias_type)
	return report

def get_connected_alias_report(handle_id : str, handle_type : HandleTypes, amount : int):
	ending = '' if amount == 0 else f' with {coin} **{amount}**'
	if handle_type == HandleTypes.Regular:
		return f'- Connected alias: regular handle **{handle_id}**{ending}\n'
	elif handle_type == HandleTypes.Burner:
		return f'- Connected alias: burner handle **{handle_id}**{ending}\n'
	elif handle_type == HandleTypes.NPC:
		return f'  [OFF: added **{handle_id}** as an NPC handle{ending}.]\n'

def get_all_connected_aliases_of_type_report(handle_type : HandleTypes):
	if handle_type == HandleTypes.Regular:
		return '\n'
	elif handle_type == HandleTypes.Burner:
		return '  (Use \".burn <burner_name>\" to destroy a burner and erase its tracks)\n\n'
	elif handle_type == HandleTypes.NPC:
		return '  [OFF: NPC handles let you act as someone else, and cannot be traced to your other handles.]\n\n'


async def setup_groups(handle : Handle, group_names : List[str]):
	report = ''
	any_found = False
	guild = server.get_guild()
	for group_name in remove_examples(group_names):
		any_found = True
		await setup_group_for_new_member(guild, group_name, handle.actor_id)
		channel = groups.get_main_channel(group_name)
		report += f'- Confirmed group membership: {channels.clickable_channel_ref(channel)}\n'
	if any_found:
		report += '  Keep in mind that you can access your groups using all your handles.\n\n'
	return report

async def setup_group_for_new_member(guild, group_name : str, actor_id : str):
	print('Entered setup_group_for_new_member')
	if groups.group_exists(group_name):
		report = await groups.add_member_from_player_id(guild, group_name, actor_id)
		print(report)
	else:
		await groups.create_new_group(guild, group_name, [actor_id])




async def setup_owned_shops(handle : Handle, shop_names : List[str]):
	report = ''
	any_found = False
	guild = server.get_guild()
	for shop_name in remove_examples(shop_names):
		shop : Shop = await setup_new_shop_for_owner(guild, shop_name, handle)
		if shop is None:
			report += f'- Failed to connect to shop **{shop_name}**. Most likely the player data entry for {handle.actor_id} is corrupt.\n\n'
		elif shop.owner_id != handle.actor_id:
			report += f'- Connected to shop **{shop_name}**. Failed to set {handle.actor_id} as owner because the shop already existed.\n\n'
		else:
			any_found = True
			report += f'- Connected to shop **{shop.name}** owned by {handle.actor_id}.\n'
			report += f'  Public storefront: {channels.clickable_channel_id_ref(shop.storefront_channel_id)}.\n'
			report += f'  Order status: {channels.clickable_channel_id_ref(shop.order_flow_channel_id)}.\n'
			shop_actor : Actor = actors.read_actor(shop.shop_id)
			report += f'  Financial status: {channels.clickable_channel_id_ref(shop_actor.finance_channel_id)}.\n'
			report += f'  Business chat hub: {channels.clickable_channel_id_ref(shop_actor.chat_channel_id)}.\n'
	if any_found:
		report += ('  As owner of a shop, you may need to grant your employees access:\n'
			+ '> .employ <handle>\n\n')
	return report


async def setup_new_shop_for_owner(guild, shop_name : str, handle : Handle):
	if shops.shop_exists(shop_name):
		shop : Shop = shops.read_shop(shop_name)
		await shops.employ(guild, handle, shop)
		return shop
	else:
		result : ActionResult = await shops.create_shop(guild, shop_name, handle.actor_id)
		if result.success:
			return shops.read_shop(shop_name)
		else:
			return None

async def setup_employed_shops(handle : Handle, shop_names : List[str]):
	report = ''
	any_found = False
	guild = server.get_guild()
	for shop_name in remove_examples(shop_names):
		any_found = True
		shop : Shop = await setup_shop_for_new_member(guild, shop_name, handle)
		if shop is None:
			report += f'- Failed to connect to shop **{shop_name}**. Please ask shop owner for assistance once they have finished their setup.'
		else:
			report += f'- Connected to shop **{shop.name}** as an employee.\n'
			report += f'  Public storefront: {channels.clickable_channel_id_ref(shop.storefront_channel_id)}.\n'
			report += f'  Order status: {channels.clickable_channel_id_ref(shop.order_flow_channel_id)}.\n'
			shop_actor : Actor = actors.read_actor(shop.shop_id)
			report += f'  Financial status: {channels.clickable_channel_id_ref(shop_actor.finance_channel_id)}.\n'
			report += f'  Business chat hub: {channels.clickable_channel_id_ref(shop_actor.chat_channel_id)}.\n'
	if any_found:
		report += '  Keep in mind that you can access your shops using all your handles.\n\n'
	return report


async def setup_shop_for_new_member(guild, shop_name : str, handle : Handle):
	if shops.shop_exists(shop_name):
		shop : Shop = shops.read_shop(shop_name)
		await shops.employ(guild, handle, shop)
		return shop


