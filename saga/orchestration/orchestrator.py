"""
saga/orchestration/orchestrator.py
Orquestador central puro en Python (sin Prefect).

Coordina la secuencia de pasos de la Saga y, ante cualquier fallo,
dispara las compensaciones en ORDEN INVERSO ESTRICTO.

Cada paso incluye un delay configurable (SAGA_STEP_DELAY_MIN/MAX)
para que el frontend y la auditoría muestren la evolución en tiempo real.
"""
import asyncio
import httpx
import os
import random
from typing import Callable, Awaitable

ACCOUNT_URL  = os.getenv("ACCOUNT_SERVICE_URL",  "http://localhost:8001")
RISK_URL     = os.getenv("RISK_SERVICE_URL",      "http://localhost:8002")
CLEARING_URL = os.getenv("CLEARING_SERVICE_URL",  "http://localhost:8003")

DELAY_MIN = float(os.getenv("SAGA_STEP_DELAY_MIN", 1))
DELAY_MAX = float(os.getenv("SAGA_STEP_DELAY_MAX", 2))


async def _step_delay():
    """Pausa observable entre pasos (2-4 s por defecto)."""
    await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


# ─────────────────────────────────────────────────────────────────────────────
# Tipo de resultado de la saga
# ─────────────────────────────────────────────────────────────────────────────
class SagaResult:
    def __init__(self, status: str, steps: list[dict], error: str | None = None):
        self.status = status   # CONFIRMADO | RECHAZADO_FONDOS | RECHAZADO_RIESGO | RECHAZADO_RED
        self.steps  = steps    # historial de pasos para el frontend
        self.error  = error

    def to_dict(self):
        return {"status": self.status, "steps": self.steps, "error": self.error}


# ─────────────────────────────────────────────────────────────────────────────
# Orquestador principal
# ─────────────────────────────────────────────────────────────────────────────
async def run_transfer_saga(
    transfer_id: str,
    source_account: str,
    target_account: str,
    amount: float,
    chaos: dict,
    notify: Callable[[dict], Awaitable[None]] | None = None,
) -> SagaResult:
    """
    Ejecuta la Saga orquestada para una transferencia bancaria.

    notify: coroutine callback que recibe un evento de estado;
            el Gateway lo usa para enviar mensajes por WebSocket.
    """
    saga_mode = "orchestration"
    steps: list[dict] = []
    completed: list[str] = []   # pasos que ya tuvieron éxito (para compensar en reversa)

    async def emit(step: str, status: str, detail: dict | None = None):
        entry = {"step": step, "status": status, **(detail or {})}
        steps.append(entry)
        if notify:
            await notify({"transfer_id": transfer_id, **entry})

    async def call(method: str, url: str, payload: dict, timeout: float = 30.0) -> dict:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(method, url, json=payload)
            resp.raise_for_status()
            return resp.json()

    # ── PASO 1: Débito contable ───────────────────────────────────────────────
    await emit("DEBIT", "STARTED")
    await _step_delay()
    try:
        result = await call("POST", f"{ACCOUNT_URL}/debit", {
            "transfer_id": transfer_id,
            "account_code": source_account,
            "amount": amount,
            "saga_mode": saga_mode,
        })
        completed.append("DEBIT")
        await emit("DEBIT", "SUCCESS", {"ledger_entry_id": result.get("ledger_entry_id")})
    except httpx.HTTPStatusError as e:
        detail = _parse_error(e)
        await emit("DEBIT", "FAILED", {"reason": detail})
        error_code = detail.get("error", "DEBIT_FAILED") if isinstance(detail, dict) else str(detail)
        status = "RECHAZADO_FONDOS" if error_code == "INSUFFICIENT_FUNDS" else "RECHAZADO_FONDOS"
        return SagaResult(status, steps, error_code)

    # ── PASO 2: Validación de riesgo / antifraude ─────────────────────────────
    await emit("RISK_VALIDATION", "STARTED")
    await _step_delay()
    try:
        result = await call("POST", f"{RISK_URL}/validate", {
            "transfer_id": transfer_id,
            "source_account": source_account,
            "amount": amount,
            "force_fraud": chaos.get("force_fraud", False),
            "saga_mode": saga_mode,
        })
        completed.append("RISK")
        await emit("RISK_VALIDATION", "SUCCESS", {"risk_score": result.get("risk_score")})
    except httpx.HTTPStatusError as e:
        detail = _parse_error(e)
        await emit("RISK_VALIDATION", "FAILED", {"reason": detail})
        # Compensar en orden inverso: solo DEBIT completado
        await _compensate(transfer_id, source_account, amount, saga_mode, completed, emit, call)
        return SagaResult("RECHAZADO_RIESGO", steps, "FRAUD_DETECTED")

    # ── PASO 3: Liquidación interbancaria ─────────────────────────────────────
    await emit("CLEARING_SETTLE", "STARTED")
    await _step_delay()
    try:
        result = await call("POST", f"{CLEARING_URL}/settle", {
            "transfer_id": transfer_id,
            "source_account": source_account,
            "target_account": target_account,
            "amount": amount,
            "force_timeout": chaos.get("force_network_timeout", False),
            "saga_mode": saga_mode,
        })
        completed.append("CLEARING")
        await emit("CLEARING_SETTLE", "SUCCESS", {"external_ref": result.get("external_ref")})
    except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
        detail = _parse_error(e) if isinstance(e, httpx.HTTPStatusError) else "NETWORK_TIMEOUT"
        await emit("CLEARING_SETTLE", "FAILED", {"reason": detail})
        # Compensar en orden inverso: RISK → DEBIT
        await _compensate(transfer_id, source_account, amount, saga_mode, completed, emit, call)
        return SagaResult("RECHAZADO_RED", steps, "NETWORK_TIMEOUT")

    # ── PASO 4: Crédito en cuenta destino ────────────────────────────────────
    await emit("CREDIT", "STARTED")
    await _step_delay()
    try:
        result = await call("POST", f"{ACCOUNT_URL}/credit", {
            "transfer_id": transfer_id,
            "account_code": target_account,
            "amount": amount,
            "saga_mode": saga_mode,
        })
        await emit("CREDIT", "SUCCESS", {"ledger_entry_id": result.get("ledger_entry_id")})
    except httpx.HTTPStatusError as e:
        detail = _parse_error(e)
        await emit("CREDIT", "FAILED", {"reason": detail})
        completed.append("CLEARING")  # clearing ya ocurrió, compensar también
        await _compensate(transfer_id, source_account, amount, saga_mode, completed, emit, call)
        return SagaResult("RECHAZADO_RED", steps, "CREDIT_FAILED")

    return SagaResult("CONFIRMADO", steps)


# ─────────────────────────────────────────────────────────────────────────────
# Compensaciones en orden inverso
# ─────────────────────────────────────────────────────────────────────────────
async def _compensate(
    transfer_id: str,
    source_account: str,
    amount: float,
    saga_mode: str,
    completed: list[str],
    emit: Callable,
    call: Callable,
):
    """Ejecuta compensaciones en el orden INVERSO de completed."""
    for step in reversed(completed):
        await _step_delay()

        if step == "CLEARING":
            await emit("COMPENSATE_CLEARING", "STARTED")
            try:
                await call("POST", f"{os.getenv('CLEARING_SERVICE_URL', 'http://localhost:8003')}/compensate/settlement", {
                    "transfer_id": transfer_id, "saga_mode": saga_mode,
                })
                await emit("COMPENSATE_CLEARING", "COMPENSATED")
            except Exception as e:
                await emit("COMPENSATE_CLEARING", "FAILED", {"reason": str(e)})

        elif step == "RISK":
            await emit("COMPENSATE_RISK", "STARTED")
            try:
                await call("POST", f"{os.getenv('RISK_SERVICE_URL', 'http://localhost:8002')}/compensate/approval", {
                    "transfer_id": transfer_id, "saga_mode": saga_mode,
                })
                await emit("COMPENSATE_RISK", "COMPENSATED")
            except Exception as e:
                await emit("COMPENSATE_RISK", "FAILED", {"reason": str(e)})

        elif step == "DEBIT":
            await emit("COMPENSATE_DEBIT", "STARTED")
            try:
                await call("POST", f"{os.getenv('ACCOUNT_SERVICE_URL', 'http://localhost:8001')}/compensate/debit", {
                    "transfer_id": transfer_id,
                    "account_code": source_account,
                    "amount": amount,
                    "saga_mode": saga_mode,
                })
                await emit("COMPENSATE_DEBIT", "COMPENSATED")
            except Exception as e:
                await emit("COMPENSATE_DEBIT", "FAILED", {"reason": str(e)})


def _parse_error(e: httpx.HTTPStatusError) -> dict | str:
    try:
        return e.response.json().get("detail", str(e))
    except Exception:
        return str(e)
