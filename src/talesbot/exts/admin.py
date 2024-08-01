from interactions import (
    Client,
    Extension,
    Guild,
    GuildCategory,
    SlashCommand,
    SlashContext,
    check,
    is_owner,
)

from ..conf import exts


class Admin(Extension):
    """Extension that handles administrative commands."""

    base_command = SlashCommand(name="admin", description="Administrative commands.")
    channels_group = base_command.group(
        name="channels", description="Channel commands."
    )

    def __init__(self, bot: Client) -> None:
        self.ext = exts(self.bot)
        self.add_ext_check(is_owner())

    @check(is_owner())
    @channels_group.subcommand(
        sub_cmd_name="init", sub_cmd_description="Initialise channels."
    )
    async def init_channels(self, ctx: SlashContext):
        """Initialise channels and groups."""
        channels = self.ext.config.channels.init
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
