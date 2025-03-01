from discord import Client, Guild, Permissions

system_roles = {
    "system": Permissions(),
    "admin": Permissions(),
    "player": Permissions(),
    "shop": Permissions(),
}


async def apply_guild_defaults(guild: Guild):
    await guild.default_role.edit(permissions=Permissions())
    role_map = {role.name: role for role in guild.roles}
    for role_name, perms in system_roles.items():
        role = role_map.get(role_name)
        if role is None:
            await guild.create_role(name=role_name, permissions=perms)
        else:
            await role.edit(permissions=perms)


def base_overrides():
    pass
