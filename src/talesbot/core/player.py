import csv
from typing import Annotated, Any

import discord
from annotated_types import T
from pydantic import BaseModel, BeforeValidator, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from talesbot.config import config_dir

from ..errors import InvalidStartingHandleError
from .database.models import Player

known_handle_file = config_dir / "known_handles.csv"


def parse_list(value: Any) -> Any:
    if isinstance(value, list):
        return value
    elif isinstance(value, str):
        if value.strip() == "":
            return []
        return [v.strip() for v in value.split(",") if v.strip() != ""]
    else:
        raise ValueError("Input should be csv string")


def parse_keyval(value: Any) -> Any:
    if isinstance(value, list):
        return {
            k: v for k, v in map(lambda x: (y.strip() for y in x.split(":")), value)
        }
    else:
        raise ValueError("Input should be csv keyval")


def parse_x_bool(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip() == "x"
    elif isinstance(value, bool):
        return value
    else:
        raise ValueError("Input should be x bool")


CsvDict = Annotated[
    dict[str, T],
    BeforeValidator(parse_keyval),
    BeforeValidator(parse_list),
]
CsvList = Annotated[list[T], BeforeValidator(parse_list)]
XBool = Annotated[bool, BeforeValidator(parse_x_bool)]


class KnownHandle(BaseModel):
    name: str = Field(validation_alias="Spelare")
    role_name: str = Field(validation_alias="Rollnamn")
    handle: str = Field(validation_alias="Main handle")
    balance: int = Field(validation_alias="Pengar på main:")
    alt_handles: CsvList[str] = Field(validation_alias="Alternativa handles")
    alt_balance: CsvDict[int] = Field(validation_alias="Pengar på övriga:")
    groups: CsvList[str] = Field(validation_alias="Grupper:")
    tacoma: XBool = Field(validation_alias="Tacoma")
    actor_id: str | None = Field(validation_alias="u-nummer")
    server: str | None = Field(validation_alias="Server")
    category: str | None = Field(validation_alias="Category")


def read_known_handles() -> dict[str, KnownHandle]:
    with open(known_handle_file) as f:
        reader = csv.DictReader(f)
        handles = [KnownHandle.model_validate(row, strict=False) for row in reader]

        return {h.handle: h for h in handles}


async def get(session: AsyncSession, discord_id: int) -> Player | None:
    return await session.scalar(select(Player).where(Player.discord_id == discord_id))


async def create(member: discord.Member, handle: str):
    known_handles = read_known_handles()
    if handle not in known_handles:
        raise InvalidStartingHandleError(handle)

    known_handle = known_handles[handle]
