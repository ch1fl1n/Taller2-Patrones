"""
saga/choreography/subscribers/clearing_subscriber.py

Escucha:
  - RISK_APPROVED  → liquida → emite CLEARING_SETTLED | CLEARING_FAILED
  - CLEARING_FAILED (propio si necesita limpiar) → emite COMPENSATE_RISK
"""
import asyncio, json, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))

import httpx
import redis.asyncio as aioredis
from saga.choreography.publisher import publish
from saga.choreography.event_schemas import CHANNELS

CLEARING_URL = os.getenv("CLEARING_SERVICE_URL", "http://localhost:8003")
DELAY_MIN    = float(os.getenv("SAGA_STEP_DELAY_MIN", 2))
DELAY_MAX    = float(os.getenv("SAGA_STEP_DELAY_MAX", 4))


async def handle(event: dict):
    etype       = event["event_type"]
    transfer_id = event["transfer_id"]
    payload     = event["payload"]

    await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    async with httpx.AsyncClient(timeout=12.0) as client:

        if etype == "RISK_APPROVED":
            resp = await client.post(f"{CLEARING_URL}/settle", json={
                "transfer_id":    transfer_id,
                "source_account": payload.get("source_account", ""),
                "target_account": payload.get("target_account", ""),
                "amount":         payload["amount"],
                "force_timeout":  payload.get("force_timeout", False),
                "saga_mode":      "choreography",
            })
            if resp.status_code == 200:
                await publish("CLEARING_SETTLED", transfer_id, {
                    **payload,
                    **resp.json(),
                })
            else:
                await publish("CLEARING_FAILED", transfer_id, {
                    "reason":         "NETWORK_TIMEOUT",
                    "source_account": payload.get("source_account", ""),
                    "amount":         payload["amount"],
                })
                # Disparar compensación en cadena: risk → debit
                await publish("COMPENSATE_RISK", transfer_id, {
                    "source_account": payload.get("source_account", ""),
                    "amount":         payload["amount"],
                    "reason":         "NETWORK_TIMEOUT",
                })


async def main():
    r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(CHANNELS["RISK_APPROVED"])
    print("[clearing-subscriber] Listening...")
    async for message in pubsub.listen():
        if message["type"] == "message":
            try:
                event = json.loads(message["data"])
                await handle(event)
            except Exception as e:
                print(f"[clearing-subscriber] Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
