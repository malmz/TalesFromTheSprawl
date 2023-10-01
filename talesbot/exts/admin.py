from interactions import (
    ChannelType,
    Extension,
    Guild,
    GuildCategory,
    SlashCommand,
    SlashContext,
    check,
    is_owner,
    slash_command,
)

from ..conf import ClientExtension, exts

base_command = SlashCommand(name="admin", description="Administrative commands.")
channels_group = base_command.group(name="channels", description="Channel commands.")


class Admin(Extension, name="admin"):
    """Extension that handles administrative commands."""

    def __init__(self) -> None:
        self.add_ext_check(is_owner())

    def exts(self) -> ClientExtension:
        return exts(self.bot)

    @check(is_owner())
    @channels_group.subcommand(
        sub_cmd_name="init", sub_cmd_description="Initialise channels."
    )
    async def init_channels(self, ctx: SlashContext):
        """Initialise channels and groups."""
        channels = self.exts().config.channels.init
        for category, channels in channels.items():
            category = await ctx.guild.create_category(category)
            for channel, description in channels.items():
                await ctx.guild.create_text_channel(
                    channel, category=category, topic=description
                )

    async def _get_or_create_category(self, guild: Guild, name: str) -> GuildCategory:
        category = next(
            (
                cat
                for cat in guild.channels
                if isinstance(cat, GuildCategory) and cat.name == name
            ),
            None,
        )
        if category is None:
            category = await guild.create_category(name)
        return category
