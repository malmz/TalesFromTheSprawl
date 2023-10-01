from ..models import Config


class BaseChecks:
    def __init__(self, config: Config):
        self.config = config
