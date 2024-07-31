from interactions import (
    Client,
    Extension,
    OptionType,
    SlashContext,
    slash_command,
    slash_option,
)


from ..db import Handle, Player, PlayerHandle, database

from ..conf import exts


class Chats(Extension):
    """Extension that handles players."""

    def __init__(self, bot: Client):
        self.ext = exts(self.bot)

    @slash_command(name="register", description="Register as a player")
    @slash_option(
        name="handle_name",
        description="Player handle",
        required=True,
        opt_type=OptionType.STRING,
    )
    async def register(self, ctx: SlashContext, handle_name: str):
        try:
            with database.atomic():
                handle = Handle.create(name=handle_name)
                player = Player.create(
                    discord_id=ctx.author_id, active_handle=handle.id
                )
                PlayerHandle.create(player=player.id, handle=handle.id)
        except:
            await ctx.send(
                f"Handle {handle_name} or discord user {ctx.author.display_name} already registerd",
                ephemeral=True,
            )
            return

        await ctx.send(
            f"Registerd player {handle_name} to discord user {ctx.author.display_name}",
            ephemeral=True,
        )
