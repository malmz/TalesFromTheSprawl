import logging
from collections.abc import Mapping

from discord import Client, Guild, Member, PermissionOverwrite, Permissions, Role

logger = logging.getLogger(__name__)


type Overrides = Mapping[Role | Member, PermissionOverwrite]

no_access = PermissionOverwrite(read_messages=False, send_messages=False)
# Will get send access depending on all_players_role settings for this channel
normal_access = PermissionOverwrite(read_messages=True)
super_access = PermissionOverwrite(read_messages=True, send_messages=True)

everyone_access = Permissions(
    read_message_history=True,
    send_messages_in_threads=True,
    use_application_commands=True,
    attach_files=True,
    embed_links=True,
    add_reactions=True,
    external_emojis=True,
)

system_roles = {
    "everyone": everyone_access,
    "system": Permissions(read_messages=True, send_messages=True),
    "admin": Permissions(read_messages=True, send_messages=True),
    "gm": Permissions(),
    "player": Permissions(),
    "shop": Permissions(),
}


async def _apply_permissions(guild: Guild, permissions: dict[str, Permissions]):
    # await guild.default_role.edit(permissions=everyone_access)

    role_map = {role.name: role for role in guild.roles}

    for role_name, perms in permissions.items():
        role = role_map.get(role_name)
        if role is None:
            logger.debug(f"Creating role {role_name}")
            await guild.create_role(name=role_name, permissions=perms)
        else:
            await role.edit(permissions=perms)


def base_overrides(guild: Guild):
    role_map = {role.name: role for role in guild.roles}
    return {
        role_map["player"]: no_access,
    }


def private_overrides(guild: Guild, role: Role) -> Overrides:
    roles = {role.name: role for role in guild.roles}
    return {
        roles["player"]: PermissionOverwrite(read_messages=False, send_messages=True),
        role: normal_access,
    }
