import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from app.core.config import settings
from app.schemas.ai import GemmaClassificationOutput, GemmaScoringOutput
from app.services.ai.base import BaseAIService
from app.services.ai.mock_scorer import DeterministicMockScorer

class GeminiAIService(BaseAIService):
    """
    Google Gemini AI Service for dataset classification and quality trust scoring.
    Uses official Google Gemini API (gemini-1.5-flash / gemini-1.5-pro / gemini-2.0-flash).
    Falls back gracefully to deterministic rule-based evaluation if API key is not configured.
    """
    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
        self.model_name = model_name or settings.GEMINI_MODEL or "gemini-1.5-flash"
        self.mock_fallback = DeterministicMockScorer()
        
        self.client_ready = False
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                self.client_ready = True
            except Exception as e:
                self.client_ready = False

    def _clean_json_markdown(self, text: str) -> str:
        """Strip markdown code block fences if present in model response."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def classify_upload(
        self,
        title: str,
        description: str,
        data_type: str,
        allowed_categories: List[Dict[str, Any]],
        sample_preview: Any = None
    ) -> Tuple[GemmaClassificationOutput, bool]:
        # If client not configured with key or provider is mock, use deterministic engine
        if not self.client_ready or settings.AI_PROVIDER == "mock":
            return self.mock_fallback.classify(title, description, data_type, allowed_categories, sample_preview)

        allowed_slugs = []
        for cat in allowed_categories:
            allowed_slugs.append(cat["slug"])
            for sub in cat.get("subcategories", []):
                allowed_slugs.append(sub["slug"])

        prompt = (
            f"You are an expert AI dataset classifier for a commercial data marketplace.\n"
            f"Dataset Metadata:\n"
            f"- Title: {title}\n"
            f"- Description: {description}\n"
            f"- Data Type: {data_type}\n"
            f"- Allowed Taxonomy Category Slugs: {', '.join(allowed_slugs)}\n"
            f"- Sample Preview: {json.dumps(sample_preview) if sample_preview else 'N/A'}\n\n"
            "Task: Classify this dataset into the most accurate primary category and subcategory from the allowed list.\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "primary_category": "<exact slug from allowed list>",\n'
            '  "subcategory": "<exact subcategory slug from allowed list or null>",\n'
            '  "secondary_categories": ["<additional slug if applicable>"],\n'
            '  "confidence": <float between 0.0 and 1.0>,\n'
            '  "tags": ["3 to 8 relevant search keywords"],\n'
            '  "reasoning": "<1-2 sentence rationale for classification>",\n'
            '  "suggested_new_category": null\n'
            "}"
        )

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            raw_text = self._clean_json_markdown(response.text)
            parsed = json.loads(raw_text)

            # Validate that primary category is within allowed taxonomy
            if parsed.get("primary_category") in allowed_slugs:
                validated = GemmaClassificationOutput(**parsed)
                return validated, False
        except Exception as e:
            # On API error, rate limit or invalid output, fall back gracefully
            pass

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
        if not self.client_ready or settings.AI_PROVIDER == "mock":
            return self.mock_fallback.score(title, description, data_type, category_slug, precheck_metrics, sample_preview)

        prompt = (
            f"You are a rigorous dataset quality evaluator for an enterprise AI data marketplace.\n"
            f"Dataset Details:\n"
            f"- Title: {title}\n"
            f"- Description: {description}\n"
            f"- Category: {category_slug}\n"
            f"- Data Type: {data_type}\n"
            f"- Pre-check Metrics: {json.dumps(precheck_metrics)}\n"
            f"- Sample Data: {json.dumps(sample_preview) if sample_preview else 'N/A'}\n\n"
            "Task: Score the dataset across Quality, Authenticity, and Metadata Accuracy (each 0.0 to 100.0).\n"
            "Provide constructive explanation and practical contributor tips for high commercial value.\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "quality": <float 0.0-100.0>,\n'
            '  "authenticity": <float 0.0-100.0>,\n'
            '  "metadata_accuracy": <float 0.0-100.0>,\n'
            '  "explanation": "<1-3 sentence evaluation summary>",\n'
            '  "tips": ["1-3 actionable quality improvement tips"]\n'
            "}"
        )

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            raw_text = self._clean_json_markdown(response.text)
            parsed = json.loads(raw_text)
            validated = GemmaScoringOutput(**parsed)
            return validated, False
        except Exception as e:
            pass

        fallback_res, _ = self.mock_fallback.score(title, description, data_type, category_slug, precheck_metrics, sample_preview)
        return fallback_res, True
