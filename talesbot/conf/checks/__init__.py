from .channels import ChannelChecks
from ..models import Config


class Checks:
    def __init__(self, config: Config):
        self.channels = ChannelChecks(config)
