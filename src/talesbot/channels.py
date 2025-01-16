"""
Tracks and handles state related to channels
"""

import asyncio
import datetime
import logging
import os
from enum import Enum
from typing import Optional, TypedDict

import discord
from discord import CategoryChannel, Guild, Role, TextChannel
from discord.abc import GuildChannel
from discord.ext import commands

from . import players, server
from .common import (
    announcements_category_name,
    chats_category_base,
    get_all_categories,
    gm_announcements_name,
    groups_category_name,
    off_category_name,
    personal_category_base,
    public_open_category_name,
    setup_category_name,
    shadowlands_category_name,
    shops_category_name,
    testing_category_name,
)
from .custom_types import PostTimestamp
from .errors import UnexpectedChannelTypeError
from .ui.register import RegisterView

logger = logging.getLogger(__name__)

public_anon_channel_name = "anon"
slowmode_delay: int = 2


class ChannelState:
    """Channel state used for message grouping"""

    last_poster: str
    last_full_post_at: datetime.datetime
    post_count: int

    def __init__(self) -> None:
        self.last_poster = ""
        self.last_full_post_at = datetime.datetime.now()
        self.post_count = 0

    def increment(self):
        self.post_count += 1
        return self.post_count >= 10

    def reset(self):
        self.post_count = 0

    def timestamp_matches(self, timestamp: datetime.datetime):
        return (
            self.last_full_post_at.hour == timestamp.hour
            and self.last_full_post_at.second == timestamp.second
        )

    def record_new_post(
        self, handle_name: str, timestamp: datetime.datetime | None
    ) -> bool:
        if timestamp is None:
            timestamp = datetime.datetime.now()

        counter_limit = self.increment()
        if (
            self.last_poster != handle_name
            or counter_limit
            or not self.timestamp_matches(timestamp)
        ):
            self.last_full_post_at = timestamp
            self.last_poster = handle_name
            self.reset()
            return True

        return False


class ChannelStateManager:
    data: dict[str, ChannelState] = {}

    def clear(self):
        self.data.clear()

    def init_channel(self, channel_name: str):
        self.data[channel_name] = ChannelState()

    def get_state(self, channel_name: str) -> ChannelState:
        if channel_name not in self.data:
            self.init_channel(channel_name)

        return self.data[channel_name]

    def set_last_poster(self, channel_name: str, handle_name: str):
        state = self.get_state(channel_name)
        state.last_poster = handle_name

    def increment_post_count(self, channel_name: str) -> bool:
        state = self.get_state(channel_name)
        state.post_count += 1
        return state.post_count >= 10

    def reset_post_count(self, channel_name: str):
        state = self.get_state(channel_name)
        state.post_count = 0

    def record_new_post(
        self, channel_name: str, handle_name: str, timestamp: datetime.datetime
    ) -> bool:
        """Returns True if the new post should be a full post
        (with sender and timestamp header)
        Returns False if the new post should only include the content itself
        """

        state = self.get_state(channel_name)
        return state.record_new_post(handle_name, timestamp)


channel_states = ChannelStateManager()


### Utilities:


def fmt_channel(channel: GuildChannel, with_type=False) -> str:
    type_str = f" ({channel.type})" if with_type else ""
    if channel.category is not None:
        return f"{channel.guild.name}:{channel.category.name}:{channel.name}{type_str}"
    else:
        return f"{channel.guild.name}:{channel.name}{type_str}"


def clickable_channel_ref(channel: GuildChannel):
    return clickable_channel_id_ref(channel.id)


def clickable_channel_id_ref(channel_id: str | int):
    return f"<#{channel_id}>"


def _category_name(channel: GuildChannel):
    return None if channel.category is None else channel.category.name


def is_offline_channel(channel: GuildChannel):
    return _category_name(channel) == off_category_name


def is_public_channel(channel: GuildChannel):
    return (
        _category_name(channel) == public_open_category_name
        or _category_name(channel) == shadowlands_category_name
    )


def is_announcement_channel(channel: GuildChannel):
    return _category_name(channel) == announcements_category_name


def is_chat_channel(channel: GuildChannel):
    if channel.category is None:
        return False
    else:
        return channel.category.name.startswith(chats_category_base)


def is_personal_channel(channel: GuildChannel, channel_suffix: str | None = None):
    return is_category_channel(channel, personal_category_base, channel_suffix)


def is_group_channel(channel: GuildChannel, channel_suffix: str | None = None):
    return is_category_channel(channel, groups_category_name, channel_suffix)


def is_category_channel(
    channel: GuildChannel, category_name: str, channel_suffix: str | None = None
):
    if channel.category is None:
        return False
    else:
        if channel.category.name.startswith(category_name):
            if channel_suffix is None:
                return True
            else:
                return channel.name.endswith(channel_suffix)


# TODO: allow for "manual shops",
# e.g. channels under shops_category_name that are
# nonetheless handled just like public_open_category_name


class ChannelType(Enum):
    OFF = "off"
    ANON = "anon"
    OPEN = "open"
    SHOP = "shop"


def channel_type(channel: GuildChannel) -> ChannelType:
    if is_anonymous_channel(channel):
        return ChannelType.ANON
    # TODO: fill in rest
    return ChannelType.OFF


def is_shop_channel(channel: GuildChannel):
    return _category_name(channel) == shops_category_name or channel.name == os.getenv(
        "MAIN_SHOP_NAME"
    )


def is_pseudonymous_channel(channel: GuildChannel):
    return _category_name(channel) in [
        public_open_category_name,
        shadowlands_category_name,
        groups_category_name,
    ]


def is_anonymous_channel(channel: GuildChannel):
    return channel.name == public_anon_channel_name


def get_discord_channels_from_name(channel_name: str):
    return [
        ch
        for guild in server.get_guilds()
        for ch in guild.channels
        if ch.name == channel_name
    ]


def get_discord_channel(channel_id: str, guild_id: int | None = None):
    # We should make sure the channel is in the correct guild here, but leaving
    # that for the future. Channel IDs shouldnt overlap between guilds unless a
    # really unusual match appears. Let's pray to the RNG gods. Or make guild_id
    # a non-optional arg.
    for guild in server.get_guilds():
        if guild.id == guild_id or guild_id is None:
            ch = guild.get_channel(int(channel_id))
            if ch:
                return ch


async def delete_discord_channel(channel_id: str, guild_id: int | None = None):
    channel = get_discord_channel(channel_id, guild_id)
    if channel is not None:
        await channel.delete()


# TODO: idea: a "do actions muted" function, that would remove
# all non-system permissions, do action (callable?) and then re-add
# them to avoid notifications

### Common init functions:


async def init(bot: commands.Bot):
    channel_states.clear()

    logger.debug(f"Init channels for {len(bot.guilds)} guilds")
    for guild in bot.guilds:
        logger.debug(f"Processing guild {guild.name}")
        await init_channels_and_categories(guild)


async def init_channels_and_categories(guild: Guild):
    for category_name, channel_names in get_all_categories():
        category = await _verify_category_exists(guild, category_name)
        for channel_name in channel_names:
            await _verify_channel_exists(category, channel_name)

    for c in guild.channels:
        logging.debug(f"Setting roles for {c.name}")
        await _init_discord_channel(c)


async def _init_discord_channel(discord_channel: GuildChannel):
    if discord_channel.type in [
        discord.ChannelType.category,
        discord.ChannelType.voice,
    ]:
        # No need to do anything for the categories themselves or the voice channels
        return

    if discord_channel.category is not None:
        if discord_channel.category.name.startswith(personal_category_base):
            await _init_private_channel(discord_channel)
        elif (
            discord_channel.category.name == public_open_category_name
            or discord_channel.category.name == shadowlands_category_name
        ):
            if discord_channel.name == os.getenv("MAIN_SHOP_NAME"):
                # Special case: If shop is in a public open category
                await _init_common_read_only_channel(discord_channel)
            else:
                await _init_public_open_channel(discord_channel)
        elif discord_channel.category.name == shops_category_name:
            await _init_common_read_only_channel(discord_channel)
        elif discord_channel.category.name == groups_category_name:
            await _init_group_channel(discord_channel)
        elif discord_channel.category.name == announcements_category_name:
            if discord_channel.name == gm_announcements_name:
                await _init_private_channel(discord_channel, gm_extra_access=True)
            else:
                await _init_common_read_only_channel(discord_channel)
        elif discord_channel.category.name == setup_category_name:
            await _init_setup_channel(discord_channel)
        elif discord_channel.category.name == testing_category_name:
            await _init_private_channel(discord_channel, gm_extra_access=True)

    else:
        logger.debug(
            f"Will not create channel state for channel {discord_channel.name}"
            " which has no category"
        )


async def _verify_category_exists(guild: Guild, category_name: str) -> CategoryChannel:
    category = discord.utils.find(lambda c: c.name == category_name, guild.categories)
    if category is None:
        category = await guild.create_category(category_name)
        logger.debug(f"Created {fmt_channel(category, with_type=True)}")
    return category


async def _verify_channel_exists(category: CategoryChannel, channel_name: str):
    channel = discord.utils.find(lambda c: c.name == channel_name, category.channels)
    if channel is None:
        channel = await category.create_text_channel(channel_name)
        logger.debug(f"Created {fmt_channel(channel, with_type=True)}")

    if not isinstance(channel, TextChannel):
        logger.warning(f"{fmt_channel(channel, with_type=True)} is not a text channel")

    return channel


async def _set_slow_mode(channel: GuildChannel):
    if isinstance(channel, TextChannel):
        await channel.edit(slowmode_delay=slowmode_delay)
    else:
        logger.warning(
            f"Tried to set slow mode on non text channel {fmt_channel(channel)}"
        )


async def _set_base_permissions(
    discord_channel: GuildChannel,
    private: bool,
    read_only: bool,
    gm_extra_access: bool = False,
):
    add_roles_tasks = [
        asyncio.create_task(discord_channel.set_permissions(role, overwrite=overwrites))
        for (role, overwrites) in server.generate_base_overwrites(
            discord_channel.guild, private, read_only, gm_extra_access
        ).items()
    ]
    await asyncio.gather(*add_roles_tasks)


async def _init_common_read_only_channel(channel: GuildChannel, gm_only: bool = False):
    await _set_base_permissions(
        channel, private=gm_only, read_only=True, gm_extra_access=gm_only
    )
    await _set_slow_mode(channel)
    channel_states.init_channel(channel.name)


async def _init_public_open_channel(channel: GuildChannel):
    await _set_base_permissions(channel, private=False, read_only=False)
    await _set_slow_mode(channel)
    channel_states.init_channel(channel.name)


async def _init_private_channel(channel: GuildChannel, gm_extra_access: bool = False):
    read_only = is_read_only_private_channel(channel)
    await _set_base_permissions(
        channel,
        private=True,
        read_only=read_only,
        gm_extra_access=gm_extra_access,
    )
    await _set_slow_mode(channel)
    channel_states.init_channel(channel.name)


async def _init_group_channel(channel: GuildChannel):
    await _set_base_permissions(
        channel, private=True, read_only=False, gm_extra_access=True
    )
    await _set_slow_mode(channel)
    channel_states.init_channel(channel.name)


async def _init_setup_channel(channel: GuildChannel):
    if not isinstance(channel, TextChannel):
        raise UnexpectedChannelTypeError(
            f"Expected text channel {fmt_channel(channel)}"
        )

    add_roles_tasks = [
        asyncio.create_task(channel.set_permissions(role, overwrite=overwrites))
        for (role, overwrites) in server.generate_setup_channel_overwrites(
            channel.guild
        ).items()
    ]
    await asyncio.gather(*add_roles_tasks)
    await _set_slow_mode(channel)
    channel_states.init_channel(channel.name)
    await channel.purge()
    await channel.send(generate_setup_channel_welcome_msg(), view=RegisterView())


async def make_read_only(channel_id: str, guild_id: int | None = None):
    channel = get_discord_channel(channel_id, guild_id)
    if channel is not None and isinstance(channel, TextChannel):
        await _set_base_permissions(channel, private=True, read_only=True)


### Anonymous channels:


def get_public_anon_channels():
    return get_discord_channels_from_name(public_anon_channel_name)


### Private channels:
# Only visible to some players


async def create_discord_channel(
    guild: Guild, overwrites, channel_name: str, category_name: str
) -> TextChannel:
    category = await _verify_category_exists(guild, category_name)
    channel = await guild.create_text_channel(
        channel_name,
        overwrites=overwrites,
        category=category,
        slowmode_delay=slowmode_delay,
    )
    await _set_slow_mode(channel)
    channel_states.init_channel(channel.name)
    return channel


### Personal channels: completely belonging to and owned by one player

cmd_line_base = "cmd_line_"
finance_base = "finance_"
daemon_base = "daemon_"
chat_hub_base = "chat_hub_"
order_flow_base = "orders_"

# TODO: some sort of dictionary for these, with an enum type


async def delete_all_personal_channels(channel_suffix: str | None = None):
    channels_list = await get_all_personal_channels(channel_suffix)
    task_list = (asyncio.create_task(c.delete()) for c in channels_list)
    await asyncio.gather(*task_list)


async def get_all_personal_channels(channel_suffix: str | None = None):
    channel_list = await server.get_all_channels()
    return [c for c in channel_list if is_personal_channel(c, channel_suffix)]


async def get_all_chat_hub_channels(channel_suffix: str | None = None):
    channel_list = await server.get_all_channels()

    def is_match(channel_name: str):
        return is_chat_hub(channel_name) and (
            channel_suffix is None or channel_name.endswith(channel_suffix)
        )

    return [c for c in channel_list if is_match(c.name)]


async def create_personal_channel(
    guild: Guild,
    role: Role,
    channel_name: str,
    actor_id: str,
    category_index: int | None = None,
    read_only: bool = False,
):
    if category_index is None:
        category_index = players.get_player_category_index(actor_id)
    overwrites = server.generate_overwrites_own_new_private_channel(role, read_only)
    category_name = f"{personal_category_base}{category_index}"
    return await create_discord_channel(guild, overwrites, channel_name, category_name)


async def create_group_channel(guild, role, channel_name: str, read_only: bool = False):
    overwrites = server.generate_overwrites_own_new_private_channel(role, read_only)
    channel = await create_discord_channel(
        guild, overwrites, channel_name, groups_category_name
    )
    await _init_group_channel(channel)
    return channel


async def create_order_flow_channel(guild, role, shop_name: str):
    discord_channel_name = get_order_flow_name(shop_name)
    return await create_personal_channel(guild, role, discord_channel_name, shop_name)


def get_cmd_line_name(player_id: str):
    return cmd_line_base + player_id


def is_cmd_line(channel_name: str):
    return channel_name.startswith(cmd_line_base)


def get_finance_name(actor_id: str):
    return finance_base + actor_id


def is_finance(channel_name: str):
    return channel_name.startswith(finance_base)


def get_chat_hub_name(actor_id: str):
    return chat_hub_base + actor_id


def is_chat_hub(channel_name: str):
    return channel_name.startswith(chat_hub_base)


def get_order_flow_name(shop_name: str):
    return order_flow_base + shop_name


def is_order_flow(channel_name: str):
    return channel_name.startswith(order_flow_base)


# Some of the private channels (not available to all players) are read-only
def is_read_only_private_channel(channel):
    return (
        is_finance(channel.name)
        or is_order_flow(channel.name)
        or is_announcement_channel(channel)
    )


### Group channels:


async def delete_all_group_channels(channel_suffix: str | None = None):
    channels_list = await get_all_groups_channels(channel_suffix)
    task_list = (asyncio.create_task(c.delete()) for c in channels_list)
    await asyncio.gather(*task_list)


async def get_all_groups_channels(channel_suffix: str | None = None):
    channel_list = await server.get_all_channels()
    return [c for c in channel_list if is_group_channel(c, channel_suffix)]


### Chat channels:
# These are weird: the "channel" is not the discord channel, but rather a name that can be used to fetch one or more channels
# from the chats.py module


def init_chat_channel(channel_name: str):
    channel_states.init_channel(channel_name)


async def create_chat_session_channel_no_role(
    guild, discord_channel_name: str, read_only: bool = False, category_index: int = 0
):
    base_overwrites = server.generate_base_overwrites(
        guild, private=True, read_only=read_only
    )
    return await create_discord_channel(
        guild,
        base_overwrites,
        discord_channel_name,
        "%s%d" % (chats_category_base, category_index),
    )


async def delete_all_chats():
    channel_list = await get_all_chat_channels()
    task_list = (asyncio.create_task(c.delete()) for c in channel_list)
    await asyncio.gather(*task_list)


async def get_all_chat_channels():
    channel_list = await server.get_all_channels()
    return [c for c in channel_list if is_chat_channel(c)]


### Shop channels:
# These are public (open to all players) but read-only
# The idea is that the channel holds the menu items as messages, and players can react to place their orders


async def create_shop_channel(guild, channel_name: str):
    overwrites = server.generate_base_overwrites(guild, private=False, read_only=True)
    category_name = (
        public_open_category_name
        if channel_name == os.getenv("MAIN_SHOP_NAME")
        else shops_category_name
    )
    return await create_discord_channel(guild, overwrites, channel_name, category_name)


async def delete_all_shops():
    channel_list = await get_all_shop_related_channels()
    task_list = (asyncio.create_task(c.delete()) for c in channel_list)
    await asyncio.gather(*task_list)


async def get_all_shop_related_channels():
    channel_list = await server.get_all_channels()
    return [c for c in channel_list if is_shop_channel(c) or is_order_flow(c.name)]


### Landing page channel

landing_page = "landing_page"


def is_landing_page(channel_name: str):
    return channel_name == landing_page


def generate_setup_channel_welcome_msg():
    return (
        "Welcome to the in-game matrix system! In order for you to join the game, "
        "we must know your main **handle**. "
        "Your starting money, access to private networks etc. are tied to this."
        "\n\n"
        'To join, either press the "Register as player" button below'
        'or type "**/join** *handle*" in the chat.\n'
        'For example, if you are shadow_weaver, type "/join shadow_weaver"'
        "\n\n"
        "If you are not sure what your main handle is, please contact the organizers.\n"
        "==============================="
    )
