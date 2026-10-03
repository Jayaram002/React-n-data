import json
import httpx
from typing import Dict, Any, List, Optional, Tuple
from app.core.config import settings
from app.schemas.ai import GemmaClassificationOutput, GemmaScoringOutput
from app.services.ai.base import BaseAIService
from app.services.ai.mock_scorer import DeterministicMockScorer

class GemmaAIService(BaseAIService):
    def __init__(self, ollama_url: str = None, model: str = None):
        self.ollama_url = ollama_url or settings.OLLAMA_ENDPOINT
        self.model = model or settings.GEMMA_MODEL
        self.mock_fallback = DeterministicMockScorer()

    def _call_ollama(self, prompt: str) -> Optional[str]:
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json"
                    }
                )
                if res.status_code == 200:
                    return res.json().get("response")
        except Exception:
            return None
        return None

    def classify_upload(
        self,
        title: str,
        description: str,
        data_type: str,
        allowed_categories: List[Dict[str, Any]],
        sample_preview: Any = None
    ) -> Tuple[GemmaClassificationOutput, bool]:
        # If AI_PROVIDER is mock, directly use mock scorer
        if settings.AI_PROVIDER == "mock":
            return self.mock_fallback.classify(title, description, data_type, allowed_categories, sample_preview)

        # Prepare allowed category slug list
        allowed_slugs = []
        for cat in allowed_categories:
            allowed_slugs.append(cat["slug"])
            for sub in cat.get("subcategories", []):
                allowed_slugs.append(sub["slug"])

        prompt = (
            f"You are a strict data classification assistant. Classify the following {data_type} dataset:\n"
            f"Title: {title}\n"
            f"Description: {description}\n"
            f"Allowed category slugs: {', '.join(allowed_slugs)}\n\n"
            "Return ONLY a JSON object matching this schema:\n"
            "{\n"
            '  "primary_category": "<slug from allowed list>",\n'
            '  "subcategory": "<slug from allowed list or null>",\n'
            '  "secondary_categories": ["<slug>"],\n'
            '  "confidence": 0.0-1.0,\n'
            '  "tags": ["3-8 searchable keywords"],\n'
            '  "reasoning": "<1-2 sentences>",\n'
            '  "suggested_new_category": null\n'
            "}"
        )

        for attempt in range(2): # Try twice
            raw_response = self._call_ollama(prompt)
            if raw_response:
                try:
                    parsed = json.loads(raw_response)
                    # Validate slug exists in allowed list
                    if parsed.get("primary_category") in allowed_slugs:
                        validated = GemmaClassificationOutput(**parsed)
                        return validated, False
                except Exception:
                    pass

        # Fallback to Mock Scorer with degraded=True
        fallback_res, _ = self.mock_fallback.classify(title, description, data_type, allowed_categories, sample_preview)
        return fallback_res, True

    def score_upload(
        self,
        title: str,
        description: str,
        data_type: str,
        category_slug: str,
        precheck_metrics: Dict[str, Any],
        sample_preview: Any = None
    ) -> Tuple[GemmaScoringOutput, bool]:
        if settings.AI_PROVIDER == "mock":
            return self.mock_fallback.score(title, description, data_type, category_slug, precheck_metrics, sample_preview)

        prompt = (
            f"You are a rigorous dataset quality evaluator. Evaluate this {data_type} dataset:\n"
            f"Title: {title}\n"
            f"Description: {description}\n"
            f"Category: {category_slug}\n"
            f"Precheck metrics: {json.dumps(precheck_metrics)}\n\n"
            "Return ONLY a JSON object matching this schema:\n"
            "{\n"
            '  "quality": 0.0-100.0,\n'
            '  "authenticity": 0.0-100.0,\n'
            '  "metadata_accuracy": 0.0-100.0,\n'
            '  "explanation": "<1-3 sentences>",\n'
            '  "tips": ["1-3 tips"]\n'
            "}"
        )

        for attempt in range(2):
            raw_response = self._call_ollama(prompt)
            if raw_response:
                try:
                    parsed = json.loads(raw_response)
                    validated = GemmaScoringOutput(**parsed)
                    return validated, False
                except Exception:
                    pass

        fallback_res, _ = self.mock_fallback.score(title, description, data_type, category_slug, precheck_metrics, sample_preview)
        return fallback_res, True
