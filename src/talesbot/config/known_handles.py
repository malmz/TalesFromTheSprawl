from typing import List, NamedTuple

from pydantic import BaseModel


class Handle(NamedTuple):
    name: str
    balance: int


class KnownHandles(BaseModel):
    handles: List[Handle] = []
    npc_handles: List[Handle] = []
    burners: List[Handle] = []
    groups: List[str] = []
    shop_owner: List[str] = []
    shop_employee: List[str]
