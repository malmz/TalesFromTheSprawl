from pathlib import PurePath

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

config_dir = PurePath("config")


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    HOST: str = "127.0.0.1"
    PORT: int = 5000

    DISCORD_TOKEN: str
    APPLICATION_ID: int
    SQLALCHEMY_DATABASE_URI: str = Field(alias="DATABASE_URI")

    GUILD_NAME: str
    GM_ROLE_NAME: str
    MAIN_SHOP_NAME: str
    FILE_LOGGING: bool
    CLEAR_ALL: bool = False
    DESTROY_ALL: bool = False


config = Config()  # type: ignore
