"""class Handle(BaseModel):
    name = TextField(unique=True)
    balance = IntegerField(default=0)


class Player(BaseModel):
    discord_id = TextField(unique=True)
    active_handle = ForeignKeyField(Handle)


class Shop(BaseModel):
    name = TextField(unique=True)


class Employee(BaseModel):
    player = ForeignKeyField(Player)
    shop = ForeignKeyField(Shop)


class Group(BaseModel):
    name = TextField(unique=True)


class GroupMember(BaseModel):
    player = ForeignKeyField(Player)
    group = ForeignKeyField(Group)


class PlayerHandle(BaseModel):
    player = ForeignKeyField(Player, backref="handles")
    handle = ForeignKeyField(Handle, backref="players")"""

from typing import List, Optional

from sqlalchemy import Column, ForeignKey, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base

player_groups = Table(
    "player_groups",
    Base.metadata,
    Column("player_id", ForeignKey("player.id"), primary_key=True),
    Column("group_id", ForeignKey("group.id"), primary_key=True),
)

player_shops = Table(
    "player_shops",
    Base.metadata,
    Column("player_id", ForeignKey("player.id"), primary_key=True),
    Column("shop_id", ForeignKey("shop.id"), primary_key=True),
)


class Sequence(Base):
    __tablename__ = "sequence"

    id: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[int]


class Actor(Base):
    __tablename__ = "actor"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str]
    role: Mapped[str]
    guild_id: Mapped[int]
    finance_id: Mapped[int]
    finance_stmt_id: Mapped[int]
    chat_id: Mapped[int]

    player: Mapped["Player"] = relationship(back_populates="actor", single_parent=True)


class Player(Base):
    __tablename__ = "player"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    discord_id: Mapped[int]
    guild_id: Mapped[int]
    actor_id: Mapped[int] = mapped_column(ForeignKey("actor.id"))
    category: Mapped[int]
    cmd_channel: Mapped[int]

    actor: Mapped["Actor"] = relationship(back_populates="player")

    groups: Mapped[List["Group"]] = relationship(
        secondary=player_groups, back_populates="members"
    )
    shops: Mapped[List["Shop"]] = relationship(
        secondary=player_shops, back_populates="members"
    )

    __table_args__ = (UniqueConstraint("actor_id"),)


class Group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    members: Mapped[List["Player"]] = relationship(
        secondary=player_groups, back_populates="groups"
    )
    name: Mapped[str]


class Shop(Base):
    __tablename__ = "shop"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    members: Mapped[List["Player"]] = relationship(
        secondary=player_shops, back_populates="shops"
    )
    name: Mapped[str]


class Artifact(Base):
    __tablename__ = "artifact"
    __table_args__ = (UniqueConstraint("name", "password"),)

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str]
    content: Mapped[str]
    password: Mapped[Optional[str]] = mapped_column(default=None)
    announce: Mapped[Optional[str]] = mapped_column(default=None)
