"""
saga/choreography/publisher.py
Publica eventos de dominio en Redis Pub/Sub.
"""
import json
import os
import asyncio
from datetime import datetime, timezone
import redis.asyncio as aioredis

from saga.choreography.event_schemas import CHANNELS

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True,
        )
    return _redis


async def publish(event_type: str, transfer_id: str, payload: dict):
    """Publica un evento en el canal correspondiente."""
    channel = CHANNELS.get(event_type)
    if not channel:
        raise ValueError(f"Unknown event type: {event_type}")

    message = json.dumps({
        "event_type": event_type,
        "transfer_id": transfer_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    })

    r = await get_redis()
    await r.publish(channel, message)
