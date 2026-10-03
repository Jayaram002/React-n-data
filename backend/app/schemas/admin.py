from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.models.upload import UploadStatus, CategorySource, DataType
from app.models.audit import FlagStatus

class ModerationItemOut(BaseModel):
    id: int
    contributor_id: int
    contributor_email: str
    contributor_name: str
    title: str
    description: str
    status: UploadStatus
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    subcategory_id: Optional[int] = None
    subcategory_name: Optional[str] = None
    category_source: CategorySource
    category_confidence: Optional[float] = None
    price_paise: Optional[int] = None
    data_type: str
    flags_count: int
    open_flags: List[Dict[str, Any]]
    ai_total_score: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ModerationActionIn(BaseModel):
    action: str # "approve", "assign_category", "flag", "unpublish", "reject"
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    reason: Optional[str] = None

class FlagResolveIn(BaseModel):
    action: str # "resolve" or "dismiss"
    notes: Optional[str] = None

class AdminCategoryCreate(BaseModel):
    name: str
    slug: str
    base_price_paise: int = 500000
    active: bool = True

class AdminCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    base_price_paise: Optional[int] = None
    active: Optional[bool] = None

class AdminSubcategoryCreate(BaseModel):
    parent_id: int
    name: str
    slug: str
    base_price_paise: Optional[int] = None
    active: bool = True

class AdminSubcategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    base_price_paise: Optional[int] = None
    active: Optional[bool] = None

class PlatformAnalyticsOut(BaseModel):
    gmv_paise: int
    platform_revenue_paise: int
    contributor_payouts_paise: int
    total_contributors: int
    total_agencies: int
    total_uploads: int
    total_active_listings: int
    total_orders_paid: int
    total_licenses_issued: int
    category_distribution: List[Dict[str, Any]]

class AuditLogOut(BaseModel):
    id: int
    actor_id: Optional[int] = None
    actor_email: Optional[str] = None
    action: str
    entity: str
    entity_id: str
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AuditLogPagination(BaseModel):
    items: List[AuditLogOut]
    total: int
    page: int
    limit: int
    total_pages: int
