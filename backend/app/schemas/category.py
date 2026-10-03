from typing import List, Optional
from pydantic import BaseModel

class SubcategoryOut(BaseModel):
    id: int
    parent_id: Optional[int]
    slug: str
    name: str
    base_price_paise: int
    active: bool
    version: int
    published_count: int = 0

    class Config:
        from_attributes = True

class CategoryTreeOut(BaseModel):
    id: int
    slug: str
    name: str
    base_price_paise: int
    active: bool
    version: int
    published_count: int = 0
    subcategories: List[SubcategoryOut] = []

    class Config:
        from_attributes = True
