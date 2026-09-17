"""
gateway/routers/transfers.py

POST /transfers       — Inicia una transferencia (orquestación o coreografía)
GET  /transfers/{id}  — Consulta estado + bitácora de auditoría
GET  /accounts        — Lista cuentas disponibles (para el frontend)
"""
import asyncio
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi import APIRouter, HTTPException, BackgroundTasks
from gateway.models import TransferRequest
from gateway.ws_manager import manager
from shared.db import get_pool

router = APIRouter()


# ─── helpers ──────────────────────────────────────────────────────────────────

async def _check_idempotency(key: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT transfer_id, status, response_cache FROM public.transfer_operations WHERE idempotency_key = $1",
            uuid.UUID(key),
        )
    return row


async def _save_idempotency(key: str, transfer_id: str, status: str, response: dict):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO public.transfer_operations (idempotency_key, transfer_id, status, response_cache)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (idempotency_key) DO UPDATE
              SET status = EXCLUDED.status, response_cache = EXCLUDED.response_cache
            """,
            uuid.UUID(key), transfer_id, status, json.dumps(response),
        )


async def _run_orchestration(transfer_id: str, req: TransferRequest):
    """Ejecuta la saga orquestada y notifica por WS en cada paso."""
    from saga.orchestration.orchestrator import run_transfer_saga

    async def notify(event: dict):
        await manager.notify(transfer_id, event)

    result = await run_transfer_saga(
        transfer_id=transfer_id,
        source_account=req.source_account,
        target_account=req.target_account,
        amount=float(req.amount),
        chaos={
            "force_fraud":           req.chaos.force_fraud,
            "force_network_timeout": req.chaos.force_network_timeout,
        },
        notify=notify,
    )

    await manager.broadcast_final(transfer_id, result.status, result.steps)

    response = result.to_dict()
    await _save_idempotency(req.idempotency_key, transfer_id, result.status, response)


async def _run_choreography(transfer_id: str, req: TransferRequest):
    """Dispara el primer evento de la coreografía y escucha el resultado final."""
    from saga.choreography.publisher import publish
    import redis.asyncio as aioredis
    from saga.choreography.event_schemas import CHANNELS

    await publish("TRANSFER_REQUESTED", transfer_id, {
        "source_account": req.source_account,
        "target_account": req.target_account,
        "amount":         float(req.amount),
        "force_fraud":    req.chaos.force_fraud,
        "force_timeout":  req.chaos.force_network_timeout,
    })

    # Suscribirse a los eventos de resultado final y reenviarlos por WS
    r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(
        CHANNELS["TRANSFER_CONFIRMED"],
        CHANNELS["TRANSFER_COMPENSATED"],
        CHANNELS["DEBIT_FAILED"],
    )

    final_status = None
    timeout = float(os.getenv("SAGA_STEP_DELAY_MAX", 4)) * 6  # esperar máx 6 pasos

    async def listen():
        nonlocal final_status
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            event = json.loads(message["data"])
            if event.get("transfer_id") != transfer_id:
                continue

            await manager.notify(transfer_id, {
                "transfer_id": transfer_id,
                "step":        event["event_type"],
                "status":      event["payload"].get("final_status", "IN_PROGRESS"),
            })

            if event["event_type"] in ("TRANSFER_CONFIRMED", "TRANSFER_COMPENSATED", "DEBIT_FAILED"):
                final_status = event["payload"].get("final_status", "RECHAZADO_FONDOS")
                break

    try:
        await asyncio.wait_for(listen(), timeout=timeout)
    except asyncio.TimeoutError:
        final_status = "TIMEOUT"
    finally:
        await pubsub.unsubscribe()
        await r.aclose()

    await manager.broadcast_final(transfer_id, final_status or "UNKNOWN", [])
    await _save_idempotency(req.idempotency_key, transfer_id, final_status or "UNKNOWN", {"status": final_status})


# ─── endpoints ────────────────────────────────────────────────────────────────

@router.post("/transfers", status_code=202)
async def create_transfer(req: TransferRequest, background_tasks: BackgroundTasks):
    # Generar idempotency key si no viene
    if not req.idempotency_key:
        req.idempotency_key = str(uuid.uuid4())

    # CP-05: verificar duplicados
    existing = await _check_idempotency(req.idempotency_key)
    if existing:
        return {
            "idempotency_key": req.idempotency_key,
            "transfer_id":     str(existing["transfer_id"]),
            "status":          existing["status"],
            "cached":          True,
            "response":        existing["response_cache"],
        }

    # CP-02: fondos insuficientes forzados antes de arrancar la saga
    if req.chaos.force_insufficient_funds:
        return {
            "idempotency_key": req.idempotency_key,
            "transfer_id":     None,
            "status":          "RECHAZADO_FONDOS",
            "cached":          False,
        }

    transfer_id = str(uuid.uuid4())

    if req.saga_mode == "orchestration":
        background_tasks.add_task(_run_orchestration, transfer_id, req)
    else:
        background_tasks.add_task(_run_choreography, transfer_id, req)

    return {
        "idempotency_key": req.idempotency_key,
        "transfer_id":     transfer_id,
        "status":          "IN_PROGRESS",
        "saga_mode":       req.saga_mode,
        "cached":          False,
    }


@router.get("/transfers/{transfer_id}/audit")
async def get_audit(transfer_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT step_name, step_status, saga_mode, payload, created_at
            FROM public.saga_audit_log
            WHERE transfer_id = $1
            ORDER BY created_at ASC
            """,
            transfer_id,
        )
    return [dict(r) for r in rows]


@router.get("/accounts")
async def list_accounts():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT account_code, owner_name, balance FROM accounts.accounts WHERE is_active = true ORDER BY account_code"
        )
    return [dict(r) for r in rows]
