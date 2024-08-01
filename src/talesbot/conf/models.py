from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    discord_token: str
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )


class ImpersonatorConfig(BaseModel):
    anon_name: str = "Anonymous"
    anon_avatar: str = "https://cdn.discordapp.com/embed/avatars/0.png"


class CategoriesConfig(BaseModel):
    metagame: str = "offline"
    setup: str = "setup"
    announcements: str = "announcements"
    general: str = "shadowlands"
    public: str = "local_network"
    shops: str = "public_buisness"
    groups: str = "private_networks"


class ChannelsConfig(BaseModel):
    anonymous: str = "anon"
    announcements: str = "announcements"
    init: dict[str, dict[str, str]] = {
        "offline": {
            "general": "Diskussion utanför spelet",
            "teknikhjälp": "Hjälp med tekniska problem",
        },
        "setup": {"landing_page": "Välkommen till Tales from the Sprawl"},
        "announcements": {"gm_alerts": "GM-annonseringar"},
        "shadowlands": {
            "seattle_news": "Seattle News",
            "open_channel": "Open Channel",
            "anon": "Anonomous Channel",
        },
        "local_network": {
            "marketplace": "Marketplace",
            "you_are_drunk": "Yoou ar vry drumk",
        },
        "public_buisness": {},
        "private_networks": {},
    }


class RolesConfig(BaseModel):
    game_master: str = "gm"
    system: str = "system"
    admin: str = "admin"
    new_player: str = "new_player"


class Config(BaseModel):
    payment_unit: str = "¥"
    channels: ChannelsConfig = ChannelsConfig()
    categories: CategoriesConfig = CategoriesConfig()
    roles: RolesConfig = RolesConfig()
    impersonator: ImpersonatorConfig = ImpersonatorConfig()
