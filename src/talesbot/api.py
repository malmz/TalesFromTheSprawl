import logging
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from talesbot import finances

from .custom_types import Transaction

logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/api/balance/{handle}")
async def balance(handle: str):
    amount = finances.get_current_balance_handle_id(handle)
    return {"amount": amount}


class Transfer(BaseModel):
    sender: Optional[str] = None
    receiver: Optional[str] = None
    amount: int


@app.post("/api/transfer")
async def transfer(data: Transfer):
    payer = data.sender if data.sender is not None else finances.system_fake_handle
    recip = data.receiver if data.receiver is not None else finances.system_fake_handle

    logger.info(f"Sending {data.amount}¥ from {payer} to {recip}")
    try:
        transaction = Transaction(payer=payer, recip=recip, amount=data.amount)
        finances.find_transaction_parties(transaction)
        await finances.record_transaction(transaction)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}
