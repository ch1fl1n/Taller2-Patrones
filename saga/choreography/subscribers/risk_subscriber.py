"""
saga/choreography/subscribers/risk_subscriber.py

Escucha:
  - DEBIT_APPLIED  → valida riesgo → emite RISK_APPROVED | RISK_REJECTED
  - COMPENSATE_RISK → revierte aprobación → emite COMPENSATE_DEBIT
"""
import asyncio, json, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))

import httpx
import redis.asyncio as aioredis
from saga.choreography.publisher import publish
from saga.choreography.event_schemas import CHANNELS

RISK_URL  = os.getenv("RISK_SERVICE_URL", "http://localhost:8002")
DELAY_MIN = float(os.getenv("SAGA_STEP_DELAY_MIN", 2))
DELAY_MAX = float(os.getenv("SAGA_STEP_DELAY_MAX", 4))


async def handle(event: dict):
    etype       = event["event_type"]
    transfer_id = event["transfer_id"]
    payload     = event["payload"]

    await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    async with httpx.AsyncClient(timeout=10.0) as client:

        if etype == "DEBIT_APPLIED":
            resp = await client.post(f"{RISK_URL}/validate", json={
                "transfer_id":    transfer_id,
                "source_account": payload.get("source_account", ""),
                "amount":         payload["amount"],
                "force_fraud":    payload.get("force_fraud", False),
                "saga_mode":      "choreography",
            })
            if resp.status_code == 200:
                await publish("RISK_APPROVED", transfer_id, {
                    **payload,
                    **resp.json(),
                })
            else:
                # Riesgo rechazado → disparar compensación del débito
                await publish("RISK_REJECTED",   transfer_id, {"reason": "RISK_REJECTED"})
                await publish("COMPENSATE_DEBIT", transfer_id, {
                    "source_account": payload.get("source_account", ""),
                    "amount":         payload["amount"],
                    "reason":         "RISK_REJECTED",
                })

        elif etype == "COMPENSATE_RISK":
            await client.post(f"{RISK_URL}/compensate/approval", json={
                "transfer_id": transfer_id,
                "saga_mode":   "choreography",
            })
            # Escalar compensación al débito
            await publish("COMPENSATE_DEBIT", transfer_id, {
                "source_account": payload.get("source_account", ""),
                "amount":         payload["amount"],
                "reason":         payload.get("reason", "NETWORK_TIMEOUT"),
            })


async def main():
    r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(
        CHANNELS["DEBIT_APPLIED"],
        CHANNELS["COMPENSATE_RISK"],
    )
    print("[risk-subscriber] Listening...")
    async for message in pubsub.listen():
        if message["type"] == "message":
            try:
                event = json.loads(message["data"])
                await handle(event)
            except Exception as e:
                print(f"[risk-subscriber] Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
