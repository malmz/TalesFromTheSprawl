from pydantic import BaseModel


class ImpersonatorConfig(BaseModel):
    anon_name: str = "Anonymous"
    anon_avatar: str = "https://cdn.discordapp.com/embed/avatars/0.png"
