"""
POST /debit  — Debita el monto de la cuenta origen.
Guarda un ledger entry y reduce el saldo atómicamente.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi import APIRouter, HTTPException
from services.account.models import DebitRequest
from shared.db import get_pool
from shared.audit import log_step

router = APIRouter()


@router.post("/debit")
async def debit(req: DebitRequest):
    await log_step(req.transfer_id, req.saga_mode, "DEBIT", "STARTED", {"account": req.account_code, "amount": str(req.amount)})

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Bloquear la fila para evitar race conditions
        account = await conn.fetchrow(
            "SELECT id, balance FROM accounts.accounts WHERE account_code = $1 AND is_active = true FOR UPDATE",
            req.account_code,
        )
        if not account:
            await log_step(req.transfer_id, req.saga_mode, "DEBIT", "FAILED", {"reason": "ACCOUNT_NOT_FOUND"})
            raise HTTPException(status_code=404, detail="ACCOUNT_NOT_FOUND")

        if account["balance"] < req.amount:
            await log_step(req.transfer_id, req.saga_mode, "DEBIT", "FAILED", {"reason": "INSUFFICIENT_FUNDS", "available": str(account["balance"])})
            raise HTTPException(status_code=422, detail={"error": "INSUFFICIENT_FUNDS", "available": str(account["balance"])})

        new_balance = account["balance"] - req.amount

        # Actualizar saldo
        await conn.execute(
            "UPDATE accounts.accounts SET balance = $1 WHERE id = $2",
            new_balance, account["id"],
        )

        # Registrar ledger entry
        entry_id = await conn.fetchval(
            """
            INSERT INTO accounts.ledger_entries
              (transfer_id, account_id, entry_type, amount, balance_before, balance_after)
            VALUES ($1, $2, 'DEBIT', $3, $4, $5)
            RETURNING id
            """,
            req.transfer_id, account["id"], req.amount,
            account["balance"], new_balance,
        )

    await log_step(req.transfer_id, req.saga_mode, "DEBIT", "SUCCESS", {"ledger_entry_id": str(entry_id), "new_balance": str(new_balance)})
    return {"ledger_entry_id": str(entry_id), "new_balance": str(new_balance)}
