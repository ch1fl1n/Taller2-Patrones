"""
Account & Ledger Service — Puerto 8001
Gestiona débitos, créditos y reversas de saldo.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from shared.db import get_pool, close_pool
from services.account.routers import debit, credit, compensate


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()  # calentar el pool al arrancar
    yield
    await close_pool()


app = FastAPI(title="Account Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(debit.router)
app.include_router(credit.router)
app.include_router(compensate.router)


@app.get("/health")
async def health():
    return {"service": "account", "status": "ok"}


@app.get("/balance/{account_code}")
async def get_balance(account_code: str):
    from shared.db import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT account_code, owner_name, balance FROM accounts.accounts WHERE account_code = $1",
            account_code,
        )
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="ACCOUNT_NOT_FOUND")
    return {"account_code": row["account_code"], "owner_name": row["owner_name"], "balance": str(row["balance"])}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.account.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8001)), reload=True)
