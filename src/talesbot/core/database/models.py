import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Table, UniqueConstraint, func
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


class Player(Base):
    __tablename__ = "player"
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    discord_id: Mapped[int]
    guild_id: Mapped[int]
    cmd_channel_id: Mapped[int]
    shops: Mapped[set["Shop"]] = relationship(
        init=False, back_populates="employees", secondary=player_shops
    )
    groups: Mapped[set["Group"]] = relationship(
        init=False, back_populates="members", secondary=player_groups
    )


class Actor(Base):
    __tablename__ = "actor"
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str]


class Group(Base):
    __tablename__ = "group"
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    members: Mapped[set["Player"]] = relationship(
        init=False, back_populates="groups", secondary=player_groups
    )


class Shop(Base):
    __tablename__ = "shop"
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    employees: Mapped[set["Player"]] = relationship(
        init=False, back_populates="shops", secondary=player_groups
    )


class Handle(Base):
    __tablename__ = "handle"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str]
    balance: Mapped[int]
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
