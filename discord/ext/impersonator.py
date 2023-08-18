from interactions import ChannelType, Extension, GuildText, listen
from interactions.api.events import MessageCreate

import channels


class Impersonator(Extension, name="impersonator"):
    """Extension that handles resending player messages as anonymous messages."""

    @listen
    async def process_messages(self, event: MessageCreate):
        game_started = True
        if (
            event.message.author.bot
            or channels.is_offline_channel(event.message.channel)
            or not isinstance(event.message.channel, GuildText)
        ):
            return

        if channels.is_anonymous_channel(event.message.channel):
            await self.send_anonomous_message(event.message)

        elif channels.is_pseudonymous_channel(message.channel):
            await posting.process_open_message(message)

        elif channels.is_chat_channel(message.channel):
            await chats.process_message(message)

    async def send_anonomous_message(self, message):
        pass
