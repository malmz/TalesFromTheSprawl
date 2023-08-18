from interactions import Client, Webhook


class Impersonator:
    def __init__(self, defaults):
        self.webooks: dict[str, Webhook] = {}
        self.defaults = defaults

    async def setup(self, bot: Client):
        pass

    async def send(self):
        pass
