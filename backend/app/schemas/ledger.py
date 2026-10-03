from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.ledger import AccountType, EntryDirection, EntryKind, PayoutStatus

class WalletOut(BaseModel):
    user_id: int
    pending_balance_paise: int
    available_balance_paise: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SaleItemOut(BaseModel):
    order_id: int
    upload_id: int
    dataset_title: str
    data_type: str
    total_amount_paise: int
    contributor_share_paise: int
    buyer_email: str
    created_at: datetime

class PayoutRequestCreate(BaseModel):
    amount_paise: int
    method: str = "bank_transfer" # "bank_transfer" or "upi"
    destination: str              # e.g., "HDFC0001234 - 501004829102" or "contributor@okhdfcbank"

class PayoutRequestOut(BaseModel):
    id: int
    user_id: int
    amount_paise: int
    status: PayoutStatus
    method: Optional[str] = "bank_transfer"
    destination: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class PayoutProcessIn(BaseModel):
    action: str # "complete" or "reject"
    reason: Optional[str] = None

class ContributorEarningsSummary(BaseModel):
    wallet: WalletOut
    lifetime_earnings_paise: int
    lifetime_withdrawn_paise: int
    sales_count: int
    recent_sales: List[SaleItemOut]
    payout_requests: List[PayoutRequestOut]
