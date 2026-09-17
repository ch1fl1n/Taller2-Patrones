"""
POST /compensate/approval — Reversa de la aprobación de riesgo.
Idempotente: si ya está REVERSED no hace nada.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi import APIRouter, HTTPException
from services.risk.models import CompensateApprovalRequest
from shared.db import get_pool
from shared.audit import log_step

router = APIRouter()


@router.post("/compensate/approval")
async def compensate_approval(req: CompensateApprovalRequest):
    await log_step(req.transfer_id, req.saga_mode, "COMPENSATE_RISK", "STARTED", {})

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, status FROM risk.validations WHERE transfer_id = $1",
            req.transfer_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="VALIDATION_NOT_FOUND")

        if row["status"] == "REVERSED":
            await log_step(req.transfer_id, req.saga_mode, "COMPENSATE_RISK", "COMPENSATED", {"note": "already_reversed"})
            return {"status": "already_reversed"}

        await conn.execute(
            "UPDATE risk.validations SET status = 'REVERSED' WHERE id = $1",
            row["id"],
        )

    await log_step(req.transfer_id, req.saga_mode, "COMPENSATE_RISK", "COMPENSATED", {})
    return {"status": "reversed", "validation_id": str(row["id"])}
