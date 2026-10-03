"""Pydantic schemas for DPDP consent framework."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ConsentDocumentOut(BaseModel):
    id: int
    purpose_code: str
    version: str
    title: str
    body_markdown: str
    sha256: str
    effective_from: datetime
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConsentDocumentCreate(BaseModel):
    purpose_code: str
    version: str
    title: str
    body_markdown: str


class ConsentRecordOut(BaseModel):
    id: int
    user_id: Optional[int]
    upload_id: Optional[int]
    order_id: Optional[int]
    purpose_code: str
    document_id: int
    document_sha256: str
    action: str
    ip: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    document_title: Optional[str] = None
    document_version: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConsentWithdrawRequest(BaseModel):
    purpose_code: str = Field(..., description="Purpose to revoke, e.g. platform_listing_license or ai_training_use")


class TakedownRequestCreate(BaseModel):
    upload_id: int
    claimant_name: str = Field(..., min_length=2, max_length=255)
    claimant_email: EmailStr
    reason: str = Field(..., description="copyright | pii_violation | unlawful | other")
    details: str = Field(..., min_length=10)


class TakedownRequestOut(BaseModel):
    id: int
    upload_id: int
    claimant_name: str
    claimant_email: str
    reason: str
    details: str
    status: str
    admin_notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeletionRequestCreate(BaseModel):
    reason: Optional[str] = Field(None, max_length=1000)


class DeletionRequestOut(BaseModel):
    id: int
    user_id: int
    status: str
    reason: Optional[str]
    admin_notes: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class DataExportOut(BaseModel):
    user_profile: Dict[str, Any]
    uploads: List[Dict[str, Any]]
    orders_and_licenses: List[Dict[str, Any]]
    consent_history: List[ConsentRecordOut]
    exported_at: datetime


class ConsentReportOut(BaseModel):
    total_active_documents: int
    total_records: int
    grants_by_purpose: Dict[str, int]
    withdrawals_by_purpose: Dict[str, int]
    uploads_with_ai_training: int
    uploads_awaiting_moderation: int
    pending_takedowns: int
    pending_deletions: int


class ConsentReacceptIn(BaseModel):
    terms_accepted: bool = False
    privacy_accepted: bool = False
