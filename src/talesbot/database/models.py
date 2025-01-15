import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Sequence,
    Table,
    UniqueConstraint,
    event,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, with_loader_criteria

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

player_actor_seq = Sequence("player_actor_seq", metadata=Base.metadata, start=200)


class Player(Base):
    __tablename__ = "player"
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    discord_id: Mapped[int] = mapped_column(unique=True)
    guild_id: Mapped[int]
    cmd_channel_id: Mapped[int]
    actor_id: Mapped[int] = mapped_column(ForeignKey("actor.id"), init=False)
    actor: Mapped["Actor"] = relationship()
    shops: Mapped[list["Shop"]] = relationship(
        init=False, back_populates="employees", secondary=player_shops
    )
    groups: Mapped[list["Group"]] = relationship(
        init=False, back_populates="members", secondary=player_groups
    )


class Actor(Base):
    __tablename__ = "actor"
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    role_name: Mapped[str]
    guild_id: Mapped[int]
    channel_index: Mapped[int]
    finance_channel_id: Mapped[int]
    chat_channel_id: Mapped[int]
    finance_stmt_msg_id: Mapped[int | None] = mapped_column(default=None)
    active_handle: Mapped["Handle"] = relationship(
        init=False,
        primaryjoin="and_(Actor.id==Handle.actor_id, Handle.is_active==True)",
    )
    handles: Mapped[list["Handle"]] = relationship(init=False, back_populates="actor")


class Group(Base):
    __tablename__ = "group"
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    members: Mapped[list["Player"]] = relationship(
        init=False, back_populates="groups", secondary=player_groups
    )


class Shop(Base):
    __tablename__ = "shop"
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    employees: Mapped[list["Player"]] = relationship(
        init=False, back_populates="shops", secondary=player_groups
    )


class HandleType(Enum):
    REGULAR = "regular"
    BURNER = "burner"
    CLOSED = "closed"
    NPC = "npc"


class Handle(Base):
    __tablename__ = "handle"
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("actor.id"), init=False)
    name: Mapped[str] = mapped_column(unique=True)
    actor: Mapped["Actor"] = relationship(back_populates="handles")
    balance: Mapped[int] = mapped_column(default=0)
    kind: Mapped[HandleType] = mapped_column(default=HandleType.REGULAR)
    auto_response: Mapped[str | None] = mapped_column(default=None)
    is_main: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=False)

    outgoing_tansfers: Mapped[list["Transaction"]] = relationship(
        init=False,
        back_populates="sender",
        primaryjoin="Handle.id==Transaction.sender_id",
    )
    incoming_transfers: Mapped[list["Transaction"]] = relationship(
        init=False,
        back_populates="receiver",
        primaryjoin="Handle.id==Transaction.receiver_id",
    )

    __table_args__ = (
        Index(
            "single_active_handle",
            actor_id,
            is_active,
            unique=True,
            postgresql_where=is_active,
        ),
    )


class Transaction(Base):
    __tablename__ = "transaction"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("handle.id"), init=False)
    receiver_id: Mapped[int | None] = mapped_column(ForeignKey("handle.id"), init=False)
    amount: Mapped[int]
    operation: Mapped[str]
    data: Mapped[str | None] = mapped_column(init=False)
    emoji: Mapped[str | None] = mapped_column(init=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), init=False, server_default=func.now()
    )

    sender: Mapped["Handle | None"] = relationship(
        back_populates="outgoing_tansfers", foreign_keys=[sender_id]
    )
    receiver: Mapped["Handle | None"] = relationship(
        back_populates="incoming_transfers", foreign_keys=[receiver_id]
    )


class ArtifactContent(Base):
    __tablename__ = "artifact_content"
    __table_args__ = (UniqueConstraint("artifact_id", "page"),)

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    artifact_id: Mapped[int] = mapped_column(ForeignKey("artifact.id"), init=False)

    content: Mapped[str]
    page: Mapped[int] = mapped_column(default=0)


class Artifact(Base):
    __tablename__ = "artifact"
    __table_args__ = (UniqueConstraint("name", "password"),)

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str]
    content: Mapped[list["ArtifactContent"]] = relationship(
        order_by=ArtifactContent.page
    )
    password: Mapped[str | None] = mapped_column(default=None)
    announcement: Mapped[str | None] = mapped_column(default=None)


class Message(Base):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("handle.id"), init=False)

    content: Mapped[str]
