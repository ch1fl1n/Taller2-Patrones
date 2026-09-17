from pydantic import BaseModel
from decimal import Decimal


class SettleRequest(BaseModel):
    transfer_id: str
    source_account: str
    target_account: str
    amount: Decimal
    force_timeout: bool = False
    saga_mode: str = "orchestration"


class CompensateSettlementRequest(BaseModel):
    transfer_id: str
    saga_mode: str = "orchestration"
