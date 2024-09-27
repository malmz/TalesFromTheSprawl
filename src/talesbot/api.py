import logging

from fastapi import FastAPI
from pydantic import BaseModel

from talesbot import finances, utils

logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/api/balance/{handle}")
async def balance(handle: str):
    amount = finances.get_current_balance_handle_id(handle)
    return {"amount": amount}


class Transfer(BaseModel):
    sender: str | None = None
    receiver: str | None = None
    amount: int
    allow_partial: bool = False


@app.post("/api/transfer")
async def transfer(data: Transfer):
    logger.info(
        f"Transfering {utils.fmt_money(data.amount)} from "
        f"{utils.fmt_handle(data.sender)} to {utils.fmt_handle(data.receiver)}"
    )
    try:
        transaction = await finances.transfer_funds(
            data.sender, data.receiver, data.amount, allow_partial=True
        )

        return {
            "status": "ok",
            "message": transaction.report,
            "amount": transaction.amount,
        }
    except Exception as e:
        logger.exception(
            f"Failed transfering {utils.fmt_money(data.amount)} from "
            f"{utils.fmt_handle(data.sender)} to {utils.fmt_handle(data.sender)}"
        )
        return {"status": "error", "msg": str(e)}
