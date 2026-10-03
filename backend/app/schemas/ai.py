from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

class GemmaClassificationOutput(BaseModel):
    primary_category: str = Field(..., description="Slug of primary domain category")
    subcategory: Optional[str] = Field(None, description="Slug of subcategory or null")
    secondary_categories: List[str] = Field(default_factory=list, max_length=2)
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence between 0.0 and 1.0")
    tags: List[str] = Field(default_factory=list, description="3-8 searchable keywords")
    reasoning: str = Field(..., description="1-2 sentences explaining the category classification")
    suggested_new_category: Optional[str] = Field(None, description="Suggested new category name if 'other' was selected")

class GemmaScoringOutput(BaseModel):
    quality: float = Field(..., ge=0.0, le=100.0)
    authenticity: float = Field(..., ge=0.0, le=100.0)
    metadata_accuracy: float = Field(..., ge=0.0, le=100.0)
    explanation: str = Field(..., description="1-3 sentences explaining the overall trust score")
    tips: List[str] = Field(default_factory=list, description="1-3 actionable tips to improve score")

class AIAnalysisOut(BaseModel):
    id: int
    upload_id: int
    model_name: str
    config_version: str
    taxonomy_version: int
    classification_output: GemmaClassificationOutput
    quality: float
    authenticity: float
    uniqueness: float
    metadata_accuracy: float
    reputation: float
    total_score: float
    explanation: str
    tips: List[str]
    degraded: bool
    ai_min_price: Optional[int] = None
    ai_max_price: Optional[int] = None
    suggested_price: Optional[int] = None

    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)
