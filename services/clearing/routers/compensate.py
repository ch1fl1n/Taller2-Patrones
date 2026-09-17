"""
POST /compensate/settlement — Cancela/revierte la liquidación.
Idempotente: si ya está CANCELLED no hace nada.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi import APIRouter, HTTPException
from services.clearing.models import CompensateSettlementRequest
from shared.db import get_pool
from shared.audit import log_step

router = APIRouter()


@router.post("/compensate/settlement")
async def compensate_settlement(req: CompensateSettlementRequest):
    await log_step(req.transfer_id, req.saga_mode, "COMPENSATE_CLEARING", "STARTED", {})

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, status FROM clearing.settlements WHERE transfer_id = $1",
            req.transfer_id,
        )

        if not row:
            # No hay settlement que revertir (fallo antes de crearse), OK
            await log_step(req.transfer_id, req.saga_mode, "COMPENSATE_CLEARING", "COMPENSATED", {"note": "no_settlement_found"})
            return {"status": "no_settlement_to_reverse"}

        if row["status"] == "CANCELLED":
            await log_step(req.transfer_id, req.saga_mode, "COMPENSATE_CLEARING", "COMPENSATED", {"note": "already_cancelled"})
            return {"status": "already_cancelled"}

        await conn.execute(
            "UPDATE clearing.settlements SET status = 'CANCELLED' WHERE id = $1",
            row["id"],
        )

    await log_step(req.transfer_id, req.saga_mode, "COMPENSATE_CLEARING", "COMPENSATED", {})
    return {"status": "cancelled", "settlement_id": str(row["id"])}
