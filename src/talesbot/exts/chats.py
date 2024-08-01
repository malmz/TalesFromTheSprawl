import io
from typing import Optional

from interactions import (
    Attachment,
    AutocompleteContext,
    Client,
    Extension,
    File,
    GuildText,
    Message,
    OptionType,
    SlashContext,
    listen,
    slash_command,
    slash_option,
)
from interactions.api.events import MessageCreate

from ..conf import exts
from ..db import Handle, Player, PlayerHandle


class Chats(Extension):
    """Extension that handles resending player messages as anonymous messages."""

    def __init__(self, bot: Client):
        self.ext = exts(self.bot)

    @slash_command(name="handle", description="Show or switch current handle")
    @slash_option(
        name="handle",
        description="Handle to switch to",
        opt_type=OptionType.STRING,
        autocomplete=True,
    )
    async def handle(self, ctx: SlashContext, handle: Optional[str] = None):
        if handle == None:
            handles = [
                player.active_handle
                for player in Player.select(Player, Handle)
                .join(Handle)
                .where(Player.discord_id == ctx.author_id)
            ]
            await ctx.send(f"Current handle is {handles[0].name}", ephemeral=True)
            return

        player = Player.get(discord_id=ctx.author_id)
        if player == None:
            await ctx.send("You are not registerd", ephemeral=True)
            return

        existing_handle = Handle.get(name=handle)

        if existing_handle != None:
            player_handle = PlayerHandle.get(
                player=player.id, handle=existing_handle.id
            )

        await ctx.send("Haha", ephemeral=True)

    @handle.autocomplete("handle")
    async def autocomplete_handle(self, ctx: AutocompleteContext):
        text = ctx.input_text
        choices = []

        query = (
            Player.select(Player, Handle)
            .join(PlayerHandle)
            .join(Handle)
            .where(Player.discord_id == ctx.author_id, Handle.name.contains(text))
            .sql()
        )

        print(query)

        for player in (
            Player.select(Player, Handle)
            .join(PlayerHandle)
            .join(Handle)
            .where(Player.discord_id == ctx.author_id, Handle.name.contains(text))
        ):
            print("player", player)
            for playerhandle in player.handles:
                print("ph", playerhandle.handle.name)
                choices.append(
                    {
                        "name": playerhandle.handle.name,
                        "value": playerhandle.handle.name,
                    }
                )

        if text != "":
            choices.append({"name": f"{text} (new)", "value": text})

        await ctx.send(choices=choices)

    @listen(MessageCreate)
    async def process_messages(self, event: MessageCreate):
        checks = self.ext.checks
        message = event.message

        if (
            message.author.bot
            or not isinstance(message.channel, GuildText)
            or checks.channels.is_offline(message.channel)
        ):
            return

        if checks.channels.is_anonymous(message.channel):
            await self.send_as(message)

        elif checks.channels.is_pseudonymous(message.channel):
            query = (
                Player.select(Player, Handle)
                .join(Handle)
                .where(Player.discord_id == message.author.id)
                .limit(1)
            )

            for player in query:
                await self.send_as(message, name=player.active_handle.name)

        elif checks.channels.is_chat(message.channel):
            # await chats.process_message(message)
            pass

    async def send_as(
        self,
        message: Message,
        name: Optional[str] = None,
        avatar: Optional[str] = None,
        channel: Optional[GuildText] = None,
    ):
        """Send a message as a user with webhook."""
        if channel == None:
            if isinstance(message.channel, GuildText):
                channel = message.channel
            else:
                raise Exception("")

        await message.delete()

        name = name or self.ext.config.impersonator.anon_name
        avatar = avatar or self.ext.config.impersonator.anon_avatar

        files = [await self.attach_to_file(a) for a in message.attachments]
        webhook = await self.ext.impersonator.webhook(channel)
        await webhook.send(
            message.content,
            username=name,
            avatar_url=avatar,
            files=files,
            thread=message.thread,
            embeds=message.embeds,
        )

    async def attach_to_file(self, attachment: Attachment):
        """Convert an attachment to a file."""
        buffer = await self.bot.http.request_cdn(attachment.url, attachment.filename)
        return File(
            file=io.BytesIO(buffer),
            file_name=attachment.filename,
            content_type=attachment.content_type,
        )
