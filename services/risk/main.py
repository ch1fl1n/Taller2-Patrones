"""
Risk & Fraud Service — Puerto 8002
Valida reglas antifraude y límites diarios.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from shared.db import get_pool, close_pool
from services.risk.routers import validate, compensate


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="Risk & Fraud Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(validate.router)
app.include_router(compensate.router)


@app.get("/health")
async def health():
    return {"service": "risk", "status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.risk.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8002)), reload=True)
