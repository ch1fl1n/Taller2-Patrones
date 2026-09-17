"""
Clearing Gateway Service — Puerto 8003
Simula la liquidación interbancaria externa.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from shared.db import get_pool, close_pool
from services.clearing.routers import settle, compensate


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="Clearing Gateway Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(settle.router)
app.include_router(compensate.router)


@app.get("/health")
async def health():
    return {"service": "clearing", "status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.clearing.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8003)), reload=True)
