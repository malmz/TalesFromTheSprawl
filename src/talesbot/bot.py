import asyncio
import logging
import os
import re
from typing import cast

import discord
from discord.app_commands import BotMissingPermissions
from discord.app_commands.errors import AppCommandError, CommandInvokeError, MissingRole
from discord.ext import commands

from talesbot import (
    actors,
    channels,
    chats,
    database,
    finances,
    game,
    gm,
    groups,
    handles,
    players,
    posting,
    reactions,
    server,
    shops,
)
from talesbot.access import player
from talesbot.config import config

from .errors import ReportError

clear_all = config.CLEAR_ALL
destroy_all = config.DESTROY_ALL

logger = logging.getLogger(__name__)
cmd_logger = logging.getLogger("talesbot.messages")


class TalesCommandTree(discord.app_commands.CommandTree):
    async def on_error(
        self, interaction: discord.Interaction[discord.Client], error: AppCommandError
    ) -> None:
        logger.error("Command error", exc_info=error)
        match error:
            case ReportError() as e:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        ephemeral=True, embed=e.to_embed()
                    )
                else:
                    await interaction.followup.send(ephemeral=True, embed=e.to_embed())
            case BotMissingPermissions():
                await interaction.response.send_message(error, ephemeral=True)
            case MissingRole():
                await interaction.response.send_message(
                    "You are not allowed to run this command.", ephemeral=True
                )
            case CommandInvokeError(__cause__=ReportError()) as e:
                report_err = cast(ReportError, e.__cause__)
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        ephemeral=True, embed=report_err.to_embed()
                    )
                else:
                    await interaction.followup.send(
                        ephemeral=True, embed=report_err.to_embed()
                    )
            case _:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "Failed command. Contact system administrator.", ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "Failed command. Contact system administrator.", ephemeral=True
                    )
                await super().on_error(interaction, error)


class TalesBot(commands.Bot):
    def __init__(self, *args, inital_extensions: list[str], **kwargs):
        super().__init__(*args, tree_cls=TalesCommandTree, **kwargs)
        self.inital_extensions = inital_extensions

    async def setup_hook(self) -> None:
        for ext in self.inital_extensions:
            await self.load_extension(ext)

    async def on_guild_available(self, guild: discord.Guild):
        logger.info(f"Connected to guild {guild.name}")
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self):
        logger.info(f"Bot started as {self.user}")
        if destroy_all:
            await self.destroy_all()
            logger.info("Cleaned up all channels, categories and roles")
            await self.close()
            return

        # TODO: move some of the initialisation to the cogs instead
        await server.init(list(self.guilds))
        await handles.init(clear_all)
        await actors.init(clear_all=clear_all)
        await players.init(clear_all=clear_all)
        if os.getenv("SKIP_CHANNELS") is None:
            await channels.init(self)
        finances.init_finances()
        await chats.init(clear_all=clear_all)
        await shops.init(clear_all=clear_all)
        await groups.init(clear_all=clear_all)
        reactions.init()
        await gm.init(clear_all=clear_all)
        game.init()
        logger.debug("Initialization complete.")
        game.start_game()

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or channels.is_offline_channel(message.channel):  # type: ignore
            # ignore messages
            return

        async with database.SessionM() as session:
            p = await player.get(session, message.author.id)

            player_name = p.name if p is not None else "[unregistered]"

            channel_name = cast(str, message.channel.name)  # type: ignore

            cmd_logger.info(
                f"{message.author.id} : {player_name} : "
                f"{channel_name} : {message.content}"  # type: ignore
            )

        # "Off messages" means starting and replying to chats with GM and similar
        only_off_messages = not game.can_process_messages()
        # await server.swallow(message, alert=False)
        # return

        if channels.is_cmd_line(channel_name):
            if only_off_messages and not has_chat_command(message):
                await server.swallow(message, alert=False)
                return
            await self.process_commands(message)
            return

        if channels.is_chat_hub(channel_name) or channels.is_landing_page(channel_name):
            if only_off_messages and not has_chat_command(message):
                await server.swallow(message, alert=False)
                return
            # TODO: fix custom help command to avoid this hack
            # The .help command does not discern between channels,
            # so we must check for it specifically since
            # we want it to work in cmd_line but not in chat_hub
            if has_help_command(message):
                should_alert = not channels.is_landing_page(channel_name)
                await server.swallow(message, alert=should_alert)
            else:
                # All our commands know if they are usable in chat hub or not,
                # and will handle the message accordingly
                # TODO: not all commands actually know this
                await self.process_commands(message)
            return

        # Trying a command in any other channel gets it swallowed:
        if has_any_command(message):
            await server.swallow(message, alert=True)
            return

        if only_off_messages:
            # Only chats with certain handles are okay
            allowed = channels.is_chat_channel(
                message.channel  # type: ignore
            ) and game.is_out_of_game_chat(message.channel)
            if not allowed:
                await server.swallow(message, alert=False)
                return

        alert_checking = asyncio.create_task(
            game.check_alerts(message.content, message.channel, str(message.author.id))
        )
        processing = asyncio.create_task(process_message(message))
        await asyncio.gather(alert_checking, processing)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.user.id:
            # Don't act on bot's own reactions to avoid loops
            return

        channel = await self.fetch_channel(payload.channel_id)
        if channels.is_offline_channel(channel):  # type: ignore
            # No bot shenanigans in the off channels
            return

        await reactions.process_reaction_add(
            payload.message_id, payload.user_id, channel, payload.emoji
        )

    async def on_member_join(self, member: discord.Member):
        await server.set_user_as_new_player(member)

    async def on_command_error(
        self,
        context: commands.Context,
        exception: commands.errors.CommandError,
    ):
        match exception:
            case commands.errors.BadArgument():
                match str(exception):
                    case 'Converting to "int" failed for parameter "amount"':
                        await context.send(
                            "Error: amount must be an integer greater than 0."
                        )
                    case 'Converting to "int" failed for parameter "price"':
                        await context.send(
                            "Error: price must be an integer greater than 0."
                        )
            case commands.errors.CommandNotFound():
                await context.send("Error: that is not a known command.")
            case _:
                await context.send(
                    "Error: unknown system error. Contact administrator."
                )
                await super().on_command_error(context, exception)

    async def destroy_all(self):
        for guild in self.guilds:
            channels = await guild.fetch_channels()
            roles = await guild.fetch_roles()
            for channel in channels:
                logger.info(f"Removing channel {channel.name}")
                await channel.delete()
            for category in guild.categories:
                logger.info(f"Removing category {category.name}")
                await category.delete()
            for role in roles:
                if role.name in [gm.role_name, "new_player"] or role.name.isdigit():
                    logger.info(f"Removing role {role.name}")
                    await role.delete()


async def process_message(message):
    if channels.is_anonymous_channel(message.channel):
        await posting.process_open_message(message, True)
        return

    if channels.is_pseudonymous_channel(message.channel):
        await posting.process_open_message(message)

    if channels.is_chat_channel(message.channel):
        await chats.process_message(message)


def has_any_command(message):
    matches = re.search(r"^\.[a-z]+", message.content)
    return matches is not None


def has_help_command(message):
    matches = re.search(r"^\.help", message.content)
    return matches is not None


def has_chat_command(message):
    matches = re.search(r"^\.chat", message.content)
    if matches is not None:
        return True
    matches = re.search(r"^\.gm_chat", message.content)
    return matches is not None
