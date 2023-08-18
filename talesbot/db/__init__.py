from peewee import *
from .tables import *


create_tables()

if __name__ == "__main__":
    with database:
        """player = Player.create(player_id=1, discord_id="123")
        handle = Handle.create(name="handle1", balance=100)
        PlayerHandle.create(player=player, handle=handle)"""
        player = Player.get(Player.player_id == 1)
        handles = player.handles()
        for handle in handles:
            print(handle.__dict__)
