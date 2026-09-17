"""
shared/audit.py
Escritura de la bitácora de auditoría en public.saga_audit_log.
Todos los servicios y el gateway lo usan para registrar cada cambio de estado.
"""
import json
from uuid import UUID
from shared.db import get_pool


async def log_step(
    transfer_id: str,
    saga_mode: str,
    step_name: str,
    step_status: str,
    payload: dict | None = None,
):
    """Inserta un registro en la tabla public.saga_audit_log."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO public.saga_audit_log
              (transfer_id, saga_mode, step_name, step_status, payload)
            VALUES ($1, $2, $3, $4, $5)
            """,
            transfer_id,
            saga_mode,
            step_name,
            step_status,
            json.dumps(payload) if payload else None,
        )
