from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict
from app.models.upload import DataType, UploadStatus
from app.models.listing import ListingStatus
from app.schemas.ai import AIAnalysisOut

class ListingContributorOut(BaseModel):
    id: int
    display_name: str
    reputation_score: float

    model_config = ConfigDict(from_attributes=True)

class ListingCategoryOut(BaseModel):
    id: int
    slug: str
    name: str
    base_price_paise: int

    model_config = ConfigDict(from_attributes=True)

class ListingItemOut(BaseModel):
    id: int
    upload_id: int
    title: str
    description: str
    status: ListingStatus
    data_type: DataType
    price_paise: int
    trust_score: float
    category: Optional[ListingCategoryOut] = None
    subcategory: Optional[ListingCategoryOut] = None
    tags: List[str] = []
    contributor: Optional[ListingContributorOut] = None
    ai_training_allowed: bool
    size: int
    published_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ListingDetailOut(BaseModel):
    id: int
    upload_id: int
    title: str
    description: str
    status: ListingStatus
    data_type: DataType
    price_paise: int
    ai_min_price: Optional[int] = None
    ai_max_price: Optional[int] = None
    category: Optional[ListingCategoryOut] = None
    subcategory: Optional[ListingCategoryOut] = None
    tags: List[str] = []
    contributor: Optional[ListingContributorOut] = None
    ai_training_allowed: bool
    ai_analysis: Optional[AIAnalysisOut] = None
    file_metadata: Dict[str, Any] = {}
    published_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ListingPaginationEnvelope(BaseModel):
    items: List[ListingItemOut]
    total: int
    page: int
    limit: int
    total_pages: int
