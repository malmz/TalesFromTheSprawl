import tomllib
from .checks import Checks
from .models import Config, EnvSettings
from ..impersonator import Impersonator


def load_config() -> Config:
    with open("config.toml", "rb") as f:
        data = tomllib.load(f)
        return Config(**data)


class ClientExtension:
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
        self.checks = Checks(self.config)


config = load_config()
