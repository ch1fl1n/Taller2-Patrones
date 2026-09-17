from pydantic import BaseModel
from decimal import Decimal


class ValidateRequest(BaseModel):
    transfer_id: str
    source_account: str
    amount: Decimal
    force_fraud: bool = False
    saga_mode: str = "orchestration"


class CompensateApprovalRequest(BaseModel):
    transfer_id: str
    saga_mode: str = "orchestration"
