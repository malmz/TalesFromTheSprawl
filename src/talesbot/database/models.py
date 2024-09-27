import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Table, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


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

    sender: Mapped["Handle"] = relationship(
        back_populates="outgoing_tansfers", foreign_keys=[sender_id]
    )
    receiver: Mapped["Handle"] = relationship(
        back_populates="incoming_transfers", foreign_keys=[receiver_id]
    )
