from discord import TextChannel

from . import Config


class Checks:
    def __init__(self, config: Config):
        self.channels = ChannelChecks(config)


class BaseChecks:
    def __init__(self, config: Config):
        self.config = config


class ChannelChecks(BaseChecks):
    def _category(self, channel: TextChannel) -> str | None:
        return channel.category.name if channel.category else None

    def is_public(self, channel: TextChannel) -> bool:
        return self._category(channel) in [
            self.config.categories.public,
            self.config.categories.general,
        ]

    def is_announcements(self, channel: TextChannel) -> bool:
        return self._category(channel) == self.config.categories.announcements

    def is_offline(self, channel: TextChannel) -> bool:
        return self._category(channel) == self.config.categories.metagame

    def is_anonymous(self, channel: TextChannel) -> bool:
        return channel.name == self.config.special_channels.anonymous

    def is_pseudonymous(self, channel: TextChannel) -> bool:
        return self._category(channel) in [
            self.config.categories.public,
            self.config.categories.general,
            self.config.categories.groups,
        ]

    def is_shop(self, channel: TextChannel) -> bool:
        return self._category(channel) == self.config.categories.shops

    def is_chat(self, channel: TextChannel) -> bool:
        return False
