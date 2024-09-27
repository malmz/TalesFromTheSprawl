from discord import Member
from .utils import fmt_handle, fmt_money


class ReportError(Exception):
    """User facing error with safe printable message"""

    def __init__(self, message: str | None) -> None:
        self.message = message if message is not None else "Oops! Something when wrong!"
        super().__init__(message)

    def __str__(self) -> str:
        messages = [
            self.message if self.message is not None else "Oops! Something when wrong!"
        ]
        inner = self.__cause__
        while inner is not None:
            match inner:
                case ReportError() as r:
                    if r.message is not None:
                        messages.append(r.message)

            inner = inner.__cause__
        return "\n".join(messages)


class InsufficientBalanceError(ReportError):
    def __init__(
        self, sender: str | None, receiver: str | None, amount: int, sender_balance: int
    ) -> None:
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.sender_balance = sender_balance

        super().__init__(
            f"Could not transfer {fmt_money(amount)} to {receiver}, "
            f"insufficient funds on {sender} ({fmt_money(sender_balance)})"
        )


class InvalidPartiesError(ReportError):
    def __init__(self, sender: str | None, receiver: str | None) -> None:
        self.sender = sender
        self.receiver = receiver
        super().__init__(
            f"Cannot transfer funds from {fmt_handle(sender)} to {fmt_handle(receiver)}"
        )


class InvalidAmountError(ReportError):
    def __init__(self, amount: int) -> None:
        self.amount = amount
        if amount < 0:
            message = f"Cannot transfer negative funds ({fmt_money(amount)})"
        elif amount == 0:
            message = "Cannot transfer zero funds"
        else:
            message = f"Cannot transfer {fmt_money(amount)}"
        super().__init__(message)


class ArtifactNotFoundError(ReportError):
    def __init__(self, name: str) -> None:
        super().__init__(f'Entity "{name}" not found. Check the spelling')


class NotRegisterdError(ReportError):
    def __init__(self, user: Member) -> None:
        super().__init__(f"User {user.name} is not registerd as a player")
