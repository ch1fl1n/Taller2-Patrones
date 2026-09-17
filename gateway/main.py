"""
API Gateway — Puerto 8000
Punto de entrada centralizado: genera UUID de idempotencia,
despacha la Saga (orquestación o coreografía) y expone WebSocket.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from shared.db import get_pool, close_pool
from gateway.routers import transfers, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="NovaBank API Gateway", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173"), "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transfers.router)
app.include_router(websocket.router)


@app.get("/health")
async def health():
    return {"service": "gateway", "status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gateway.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
