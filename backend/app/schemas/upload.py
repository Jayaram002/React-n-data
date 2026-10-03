from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from app.models.upload import UploadStatus, CategorySource, DataType

class UploadFileOut(BaseModel):
    id: int
    data_type: DataType
    mime: str
    size: int
    width: Optional[int] = None
    height: Optional[int] = None
    phash: Optional[str] = None
    exif_stripped: bool
    row_count: Optional[int] = None
    column_schema: Optional[Dict[str, Any]] = None
    content_hash: Optional[str] = None
    signature_hash: Optional[str] = None

    class Config:
        from_attributes = True

class FlagOut(BaseModel):
    id: int
    reason: str
    source: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class UploadOut(BaseModel):
    id: int
    contributor_id: int
    title: str
    description: str
    status: UploadStatus
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    category_source: CategorySource
    category_confidence: Optional[float] = None
    tags: List[str] = []
    price_paise: Optional[int] = None
    ai_min_price: Optional[int] = None
    ai_max_price: Optional[int] = None
    ai_training_allowed: bool
    consent_version: str
    consent_at: datetime
    personal_data_status: str = "none"
    lawful_basis: Optional[str] = None
    lawful_basis_note: Optional[str] = None
    evidence_storage_key: Optional[str] = None
    created_at: datetime
    file_info: Optional[UploadFileOut] = None
    flags: List[FlagOut] = []

    class Config:
        from_attributes = True

class UploadListItemOut(BaseModel):
    id: int
    title: str
    status: UploadStatus
    data_type: Optional[DataType] = None
    created_at: datetime
    size: Optional[int] = None
    category_name: Optional[str] = None

    class Config:
        from_attributes = True

class PriceUpdate(BaseModel):
    price_paise: int

class CategoryUpdate(BaseModel):
    category_id: int
    subcategory_id: Optional[int] = None

