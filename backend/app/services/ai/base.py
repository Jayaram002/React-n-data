from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from app.schemas.ai import GemmaClassificationOutput, GemmaScoringOutput

class BaseAIService(ABC):
    @abstractmethod
    def classify_upload(
        self,
        title: str,
        description: str,
        data_type: str,
        allowed_categories: List[Dict[str, Any]],
        sample_preview: Any = None
    ) -> Tuple[GemmaClassificationOutput, bool]:
        """Returns (classification_output, is_degraded)"""
        pass

    @abstractmethod
    def score_upload(
        self,
        title: str,
        description: str,
        data_type: str,
        category_slug: str,
        precheck_metrics: Dict[str, Any],
        sample_preview: Any = None
    ) -> Tuple[GemmaScoringOutput, bool]:
        """Returns (scoring_output, is_degraded)"""
        pass
