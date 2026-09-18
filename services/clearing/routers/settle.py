"""
POST /settle — Simula la liquidación interbancaria externa.
force_timeout=True simula caída de red (CP-04).
"""
import sys, os, asyncio, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi import APIRouter, HTTPException
from services.clearing.models import SettleRequest
from shared.db import get_pool
from shared.audit import log_step

router = APIRouter()


@router.post("/settle")
async def settle(req: SettleRequest):
    await log_step(req.transfer_id, req.saga_mode, "CLEARING_SETTLE", "STARTED", {"source": req.source_account, "target": req.target_account, "amount": str(req.amount)})

    # Simular timeout / caída de red (CP-04)
    if req.force_timeout:
        await log_step(req.transfer_id, req.saga_mode, "CLEARING_SETTLE", "FAILED", {"reason": "NETWORK_TIMEOUT"})
        raise HTTPException(status_code=504, detail={"error": "NETWORK_TIMEOUT", "message": "External interbank network timed out"})

    external_ref = f"CLR-{uuid.uuid4().hex[:8].upper()}"

    pool = await get_pool()
    async with pool.acquire() as conn:
        settlement_id = await conn.fetchval(
            """
            INSERT INTO clearing.settlements (transfer_id, external_ref, status, settled_at)
            VALUES ($1, $2, 'SETTLED', now())
            RETURNING id
            """,
            req.transfer_id, external_ref,
        )

    await log_step(req.transfer_id, req.saga_mode, "CLEARING_SETTLE", "SUCCESS", {"settlement_id": str(settlement_id), "external_ref": external_ref})
    return {"settlement_id": str(settlement_id), "external_ref": external_ref}
