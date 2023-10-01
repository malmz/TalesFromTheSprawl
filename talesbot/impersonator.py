from interactions import Client, Extension, GuildText, Snowflake, Webhook, listen
from interactions.api.events import Ready


class Impersonator:
    """Singleton class that handles impersonating players."""

    def __init__(self, name: str, avatar: str):
        self.webooks: dict[Snowflake, Webhook] = {}
        self.name = name
        self.avatar = avatar

    async def setup(self, bot: Client):
        """Setup the impersonator by finding all webhooks for the bot's application."""
        for guild in bot.guilds:
            webhooks = await bot.http.get_guild_webhooks(guild.id)
            for webhook in webhooks:
                if webhook["application_id"] == bot.app.id:
                    self.webooks[guild.id] = Webhook.from_dict(webhook, bot)
                    break

    async def webhook(self, channel: GuildText) -> Webhook:
        """Get the webhook for the given channel. If it doesn't exist, create it."""
        webhook = self.webooks.get(channel.guild.id)
        if not webhook:
            webhook = await channel.create_webhook(
                name=self.defaults.name, avatar=self.defaults.avatar
            )
            self.webooks[channel.guild.id] = webhook

        if webhook.channel_id != channel.id:
            await webhook.edit(channel_id=channel.id)

        return webhook
