import discord
from discord import Member

from .utils import fmt_handle, fmt_money


class ReportError(Exception):
    """User facing error with a safe printable message"""

    report: str | None

    def __init__(self, report: str | None = None, *args: object) -> None:
        self.report = report

        super().__init__(report, *args)

    def to_embed(self) -> discord.Embed:
        reports = [
            self.report if self.report is not None else "Oops! Something when wrong!"
        ]
        inner = self.__cause__
        while inner is not None:
            if isinstance(inner, ReportError) and inner.report is not None:
                reports.append(inner.report)

            inner = inner.__cause__
        body = "\n- ".join(reports)

        return discord.Embed(color=discord.Color.red(), description=body)


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
            "Cannot transfer funds from "
            f"{fmt_handle(sender)} to {fmt_handle(receiver)}"
        )


class InvalidAmountError(ReportError):
    """Invalid transaction amount"""

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
    """404 no artifact found"""

    def __init__(self, name: str) -> None:
        super().__init__(f'Artifact "{name}" not found. Check the spelling')


class NotRegisterdError(ReportError):
    """User is not registerd as a player"""

    def __init__(self, user: Member | str) -> None:
        super().__init__(
            f"User {user.name if isinstance(user, Member) else user} "
            "is not registerd as a player"
        )


class AlreadyRegisterdError(ReportError):
    """User is already registerd as a player"""

    def __init__(self, user: Member | str, player_id: str) -> None:
        super().__init__(
            f"User {user.name if isinstance(user, Member) else user} "
            f"is already registerd as player {player_id}"
        )


class InvalidStartingHandleError(ReportError):
    def __init__(self, handle: str) -> None:
        super().__init__(
            f'Failed: invalid starting handle "{handle}" '
            "(or handle is already taken)."
        )


class MissingHandleError(ReportError):
    """The Actor is missing a handles table or does not have a active handle"""

    def __init__(self, actor_id: str) -> None:
        super().__init__(f"Actor {actor_id} does not have active handle")


class UnexpectedChannelTypeError(Exception):
    pass
