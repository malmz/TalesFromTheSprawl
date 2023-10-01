from typing import Optional
from interactions import (
    Attachment,
    ChannelType,
    Client,
    Extension,
    File,
    GuildText,
    Message,
    listen,
)
from interactions.api.events import MessageCreate, Startup

from ..db import Player
from ..conf import ClientExtension, exts


class Chats(Extension, name="chats"):
    """Extension that handles resending player messages as anonymous messages."""

    def exts(self) -> ClientExtension:
        return exts(self.bot)

    @listen()
    async def process_messages(self, event: MessageCreate):
        checks = self.exts().checks
        message = event.message

        game_started = True
        if (
            message.author.bot
            or not isinstance(message.channel, GuildText)
            or checks.channels.is_offline(message.channel)
        ):
            return

        if checks.channels.is_anonymous(message.channel):
            await self.send_as(message)

        elif checks.channels.is_pseudonymous(message.channel):
            player = Player.get(discord_id=message.author.id)
            await self.send_as(message, name=player.active_handle.name)

        elif checks.channels.is_chat(message.channel):
            # await chats.process_message(message)
            pass

    async def send_as(
        self,
        message: Message,
        name: Optional[str],
        avatar: Optional[str],
        channel: Optional[GuildText],
    ):
        """Send a message as a user with webhook."""
        meta = exts(self.bot)
        if channel == None:
            if isinstance(message.channel, GuildText):
                channel = message.channel
            else:
                raise Exception("")

        name = name or meta.config.impersonator.anon_name
        avatar = avatar or meta.config.impersonator.anon_avatar

        files = [await self.attach_to_file(a) for a in message.attachments]
        webhook = await meta.impersonator.webhook(channel)
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
            file=buffer,
            filename=attachment.filename,
            content_type=attachment.content_type,
        )
