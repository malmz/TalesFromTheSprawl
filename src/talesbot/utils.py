def fmt_money(amount: int) -> str:
    return f"¥{amount}" if amount >= 0 else f"-¥{-amount}"


def fmt_handle(handle: str | None) -> str:
    return handle if handle is not None else "[system]"
