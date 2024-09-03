import tomllib
from typing import Dict
from pydantic import BaseModel, TypeAdapter
from pydantic_settings import BaseSettings, SettingsConfigDict

from .known_handles import KnownHandles

from .channels import CategoriesConfig, ChannelsConfig, SpecialChannelsConfig
from .impersonator import ImpersonatorConfig
from .roles import RolesConfig


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    discord_token: str


class Config(BaseModel):
    payment_unit: str = "¥"
    channels: ChannelsConfig = ChannelsConfig()
    categories: CategoriesConfig = CategoriesConfig()
    special_channels: SpecialChannelsConfig = SpecialChannelsConfig()
    roles: RolesConfig = RolesConfig()
    impersonator: ImpersonatorConfig = ImpersonatorConfig()


def load_config() -> Config:
    with open("config.toml", "rb") as f:
        data = tomllib.load(f)
        return Config(**data)


known_handles_adapter = TypeAdapter(Dict[str, KnownHandles])


def load_known_handles() -> Dict[str, KnownHandles]:
    with open("known_handles.toml", "rb") as f:
        data = tomllib.load(f)
        return known_handles_adapter.validate_python(data)


""" class ClientExtension:
    impersonator: Impersonator
    config: Config
    env_settings: EnvSettings
    checks: Checks

    def __init__(self):
        self.config = load_config()
        self.env_settings = EnvSettings(env_file=".env")
        self.impersonator = Impersonator(
            name="Impersonator",
            avatar="assets/Anon.jpeg",
        )
        self.checks = Checks(self.config) """


config = load_config()
known_handles = load_known_handles()
