"""
POST /validate — Evalúa reglas antifraude y límite diario.
force_fraud=True simula detección de fraude (CP-03).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi import APIRouter, HTTPException
from services.risk.models import ValidateRequest
from shared.db import get_pool
from shared.audit import log_step
from decimal import Decimal

router = APIRouter()

DAILY_LIMIT = Decimal("100000.00")
SINGLE_TX_LIMIT = Decimal("50000.00")


@router.post("/validate")
async def validate(req: ValidateRequest):
    await log_step(req.transfer_id, req.saga_mode, "RISK_VALIDATION", "STARTED", {"account": req.source_account, "amount": str(req.amount)})

    # Simular fraude forzado (CP-03)
    if req.force_fraud:
        await log_step(req.transfer_id, req.saga_mode, "RISK_VALIDATION", "FAILED", {"reason": "FRAUD_DETECTED", "risk_score": 95.0})
        raise HTTPException(status_code=422, detail={"error": "FRAUD_DETECTED", "risk_score": 95.0})

    # Regla 1: monto individual
    risk_score = float(req.amount / SINGLE_TX_LIMIT * 50)
    if req.amount > SINGLE_TX_LIMIT:
        risk_score = 90.0
        await log_step(req.transfer_id, req.saga_mode, "RISK_VALIDATION", "FAILED", {"reason": "EXCEEDS_SINGLE_TX_LIMIT", "risk_score": risk_score})
        raise HTTPException(status_code=422, detail={"error": "EXCEEDS_SINGLE_TX_LIMIT", "risk_score": risk_score})

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Regla 2: límite diario acumulado
        daily = await conn.fetchval(
            "SELECT COALESCE(total_debited, 0) FROM risk.daily_limits WHERE account_id = $1 AND date = CURRENT_DATE",
            req.source_account,
        ) or Decimal("0")

        if daily + req.amount > DAILY_LIMIT:
            await log_step(req.transfer_id, req.saga_mode, "RISK_VALIDATION", "FAILED", {"reason": "DAILY_LIMIT_EXCEEDED", "current_daily": str(daily)})
            raise HTTPException(status_code=422, detail={"error": "DAILY_LIMIT_EXCEEDED", "current_daily": str(daily)})

        # Registrar validación aprobada
        validation_id = await conn.fetchval(
            """
            INSERT INTO risk.validations (transfer_id, status, risk_score, reason)
            VALUES ($1, 'APPROVED', $2, 'All checks passed')
            RETURNING id
            """,
            req.transfer_id, risk_score,
        )

        # Actualizar límite diario
        await conn.execute(
            """
            INSERT INTO risk.daily_limits (account_id, date, total_debited)
            VALUES ($1, CURRENT_DATE, $2)
            ON CONFLICT (account_id, date)
            DO UPDATE SET total_debited = risk.daily_limits.total_debited + EXCLUDED.total_debited
            """,
            req.source_account, req.amount,
        )

    await log_step(req.transfer_id, req.saga_mode, "RISK_VALIDATION", "SUCCESS", {"validation_id": str(validation_id), "risk_score": risk_score})
    return {"validation_id": str(validation_id), "approved": True, "risk_score": risk_score}
