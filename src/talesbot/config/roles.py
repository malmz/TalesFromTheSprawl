from pydantic import BaseModel


class RolesConfig(BaseModel):
    game_master: str = "gm"
    system: str = "system"
    admin: str = "admin"
    new_player: str = "new_player"
