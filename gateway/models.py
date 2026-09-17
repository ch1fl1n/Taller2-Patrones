from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional
import uuid


class ChaosOptions(BaseModel):
    force_insufficient_funds: bool = False
    force_fraud: bool = False
    force_network_timeout: bool = False


class TransferRequest(BaseModel):
    source_account: str
    target_account: str
    amount: Decimal = Field(gt=0)
    idempotency_key: Optional[str] = None   # si no viene, el gateway lo genera
    saga_mode: str = Field(default="orchestration", pattern="^(orchestration|choreography)$")
    chaos: ChaosOptions = ChaosOptions()
