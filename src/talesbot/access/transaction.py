from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from talesbot import finances

from ..custom_types import TransTypes
from ..errors import InsufficientBalanceError, InvalidAmountError, InvalidPartiesError
from ..database.models import Handle, Transaction


async def _get_handle(session: AsyncSession, handle_name: str | None) -> None | Handle:
    if handle_name is None:
        return None

    handle = await session.scalar(select(Handle).where(Handle.name == handle_name))
    if handle is None:
        balance = finances.get_current_balance_handle_id(handle_name)
        handle = Handle(name=handle_name, balance=balance)
        session.add(handle)

    return handle


async def _broadcast_transfer():
    pass


async def transfer(
    session: AsyncSession,
    sender_handle: str | None,
    receiver_handle: str | None,
    amount: int,
    allow_partial: bool = False,
    operation=TransTypes.Transfer,
):
    if sender_handle == receiver_handle:
        raise InvalidPartiesError(sender_handle, receiver_handle)

    if amount <= 0:
        raise InvalidAmountError(amount)

    async with session.begin():
        sender = await _get_handle(session, sender_handle)
        receiver = await _get_handle(session, receiver_handle)

        # If sender is none, pull it out of this air
        sender_balance = sender.balance if sender is not None else amount

        if allow_partial:
            amount = min(amount, sender_balance)

        if sender_balance < amount:
            raise InsufficientBalanceError(
                sender_handle, receiver_handle, amount, sender_balance
            )

        if receiver is not None:
            receiver.balance += amount

        if sender is not None:
            sender.balance -= amount

        transaction = Transaction(
            sender=sender,
            receiver=receiver,
            amount=amount,
            operation=operation,
        )

        session.add(transaction)
