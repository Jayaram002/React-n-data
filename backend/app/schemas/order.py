from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, ConfigDict
from app.models.order import OrderStatus
from app.schemas.listing import ListingItemOut

class OrderCreate(BaseModel):
    listing_id: int
    buyer_agreement_accepted: Optional[bool] = None
    buyer_agreement_version: Optional[str] = None

class LicenseOut(BaseModel):
    id: int
    order_id: int
    terms_version: str
    type: str
    buyer_agreement_document_id: Optional[int] = None
    buyer_agreement_sha256: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OrderOut(BaseModel):
    id: int
    buyer_id: int
    listing_id: int
    amount_paise: int
    status: OrderStatus
    created_at: datetime
    listing: Optional[ListingItemOut] = None
    license: Optional[LicenseOut] = None

    model_config = ConfigDict(from_attributes=True)

class MockCheckoutOut(BaseModel):
    order_id: int
    listing_id: int
    listing_title: str
    contributor_name: str
    amount_paise: int
    currency: str
    status: OrderStatus
    provider_ref: str
    ai_training_allowed: bool

class MockPaymentSimulate(BaseModel):
    result: str # "paid", "failed", "cancelled"
