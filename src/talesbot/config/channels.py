from pydantic import BaseModel


class CategoriesConfig(BaseModel):
    metagame: str = "offline"
    setup: str = "setup"
    announcements: str = "announcements"
    general: str = "shadowlands"
    public: str = "local_network"
    shops: str = "public_buisness"
    groups: str = "private_networks"


class SpecialChannelsConfig(BaseModel):
    anonymous: str = "anon"


class ChannelsConfig(BaseModel):
    metagame: dict[str, str] = {}
    setup: dict[str, str] = {}
    announcements: dict[str, str] = {}
    general: dict[str, str] = {"anon": "Anonomous Channel"}
    public: dict[str, str] = {}
    shops: dict[str, str] = {}
    groups: dict[str, str] = {}
