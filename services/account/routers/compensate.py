"""
POST /compensate/debit  — Reversa del débito (transacción de compensación).
Idempotente: si ya fue revertido, retorna OK sin doble acreditación.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi import APIRouter, HTTPException
from services.account.models import CompensateDebitRequest
from shared.db import get_pool
from shared.audit import log_step

router = APIRouter()


@router.post("/compensate/debit")
async def compensate_debit(req: CompensateDebitRequest):
    await log_step(req.transfer_id, req.saga_mode, "COMPENSATE_DEBIT", "STARTED", {"account": req.account_code})

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Idempotencia: verificar si ya existe una reversa para esta transferencia
        already = await conn.fetchrow(
            """
            SELECT id FROM accounts.ledger_entries
            WHERE transfer_id = $1 AND entry_type = 'REVERSAL_DEBIT'
            """,
            req.transfer_id,
        )
        if already:
            await log_step(req.transfer_id, req.saga_mode, "COMPENSATE_DEBIT", "COMPENSATED", {"note": "already_reversed"})
            return {"status": "already_reversed", "entry_id": str(already["id"])}

        account = await conn.fetchrow(
            "SELECT id, balance FROM accounts.accounts WHERE account_code = $1 FOR UPDATE",
            req.account_code,
        )
        if not account:
            raise HTTPException(status_code=404, detail="ACCOUNT_NOT_FOUND")

        new_balance = account["balance"] + req.amount

        await conn.execute(
            "UPDATE accounts.accounts SET balance = $1 WHERE id = $2",
            new_balance, account["id"],
        )

        # Marcar el entry original como REVERSED
        await conn.execute(
            """
            UPDATE accounts.ledger_entries
            SET status = 'REVERSED'
            WHERE transfer_id = $1 AND entry_type = 'DEBIT'
            """,
            req.transfer_id,
        )

        entry_id = await conn.fetchval(
            """
            INSERT INTO accounts.ledger_entries
              (transfer_id, account_id, entry_type, amount, balance_before, balance_after)
            VALUES ($1, $2, 'REVERSAL_DEBIT', $3, $4, $5)
            RETURNING id
            """,
            req.transfer_id, account["id"], req.amount,
            account["balance"], new_balance,
        )

    await log_step(req.transfer_id, req.saga_mode, "COMPENSATE_DEBIT", "COMPENSATED", {"entry_id": str(entry_id), "restored_balance": str(new_balance)})
    return {"status": "reversed", "entry_id": str(entry_id), "restored_balance": str(new_balance)}
