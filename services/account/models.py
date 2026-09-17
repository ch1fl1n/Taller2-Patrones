from pydantic import BaseModel
from decimal import Decimal


class DebitRequest(BaseModel):
    transfer_id: str
    account_code: str
    amount: Decimal
    saga_mode: str = "orchestration"


class CreditRequest(BaseModel):
    transfer_id: str
    account_code: str
    amount: Decimal
    saga_mode: str = "orchestration"


class CompensateDebitRequest(BaseModel):
    transfer_id: str
    account_code: str
    amount: Decimal
    saga_mode: str = "orchestration"
