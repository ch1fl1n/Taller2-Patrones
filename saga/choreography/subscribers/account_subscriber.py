"""
saga/choreography/subscribers/account_subscriber.py

Escucha:
  - TRANSFER_REQUESTED → ejecuta débito → emite DEBIT_APPLIED | DEBIT_FAILED
  - CLEARING_SETTLED   → ejecuta crédito → emite CREDIT_APPLIED | TRANSFER_CONFIRMED
  - COMPENSATE_DEBIT   → revierte débito → emite TRANSFER_COMPENSATED

Corre como proceso independiente: python -m saga.choreography.subscribers.account_subscriber
"""
import asyncio, json, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))

import httpx
import redis.asyncio as aioredis
from saga.choreography.publisher import publish
from saga.choreography.event_schemas import CHANNELS

ACCOUNT_URL = os.getenv("ACCOUNT_SERVICE_URL", "http://localhost:8001")
DELAY_MIN   = float(os.getenv("SAGA_STEP_DELAY_MIN", 2))
DELAY_MAX   = float(os.getenv("SAGA_STEP_DELAY_MAX", 4))


async def handle(event: dict):
    etype       = event["event_type"]
    transfer_id = event["transfer_id"]
    payload     = event["payload"]

    await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    async with httpx.AsyncClient(timeout=10.0) as client:

        if etype == "TRANSFER_REQUESTED":
            resp = await client.post(f"{ACCOUNT_URL}/debit", json={
                "transfer_id":  transfer_id,
                "account_code": payload["source_account"],
                "amount":       payload["amount"],
                "saga_mode":    "choreography",
            })
            if resp.status_code == 200:
                await publish("DEBIT_APPLIED", transfer_id, {
                    "source_account":  payload["source_account"],
                    "amount":          payload["amount"],
                    "target_account":  payload["target_account"],
                    "force_fraud":     payload.get("force_fraud", False),
                    "force_timeout":   payload.get("force_timeout", False),
                    **resp.json(),
                })
            else:
                detail = resp.json().get("detail", {})
                error  = detail.get("error", "DEBIT_FAILED") if isinstance(detail, dict) else str(detail)
                await publish("DEBIT_FAILED", transfer_id, {"reason": error, "source_account": payload["source_account"]})

        elif etype == "CLEARING_SETTLED":
            resp = await client.post(f"{ACCOUNT_URL}/credit", json={
                "transfer_id":  transfer_id,
                "account_code": payload["target_account"],
                "amount":       payload["amount"],
                "saga_mode":    "choreography",
            })
            if resp.status_code == 200:
                await publish("CREDIT_APPLIED",      transfer_id, resp.json())
                await publish("TRANSFER_CONFIRMED",  transfer_id, {"final_status": "CONFIRMADO"})
            else:
                await publish("CLEARING_FAILED", transfer_id, {"reason": "CREDIT_FAILED"})

        elif etype == "COMPENSATE_DEBIT":
            resp = await client.post(f"{ACCOUNT_URL}/compensate/debit", json={
                "transfer_id":  transfer_id,
                "account_code": payload["source_account"],
                "amount":       payload["amount"],
                "saga_mode":    "choreography",
            })
            status = "RECHAZADO_RIESGO" if payload.get("reason") == "RISK_REJECTED" else "RECHAZADO_RED"
            await publish("TRANSFER_COMPENSATED", transfer_id, {"final_status": status})


async def main():
    r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(
        CHANNELS["TRANSFER_REQUESTED"],
        CHANNELS["CLEARING_SETTLED"],
        CHANNELS["COMPENSATE_DEBIT"],
    )
    print("[account-subscriber] Listening...")
    async for message in pubsub.listen():
        if message["type"] == "message":
            try:
                event = json.loads(message["data"])
                await handle(event)
            except Exception as e:
                print(f"[account-subscriber] Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
