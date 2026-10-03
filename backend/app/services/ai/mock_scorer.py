import re
from typing import Dict, Any, List, Optional, Tuple
from app.schemas.ai import GemmaClassificationOutput, GemmaScoringOutput

# Domain keyword mapping
DOMAIN_KEYWORDS = {
    "physics": {
        "domain": "physics",
        "subs": {
            "physics-mechanics": ["velocity", "acceleration", "motion", "force", "mechanics", "sensor", "kinetic", "gravity", "torque"],
            "physics-optics": ["light", "laser", "photon", "optics", "refraction", "wavelength", "lens", "spectrum"],
            "physics-quantum": ["quantum", "spin", "entanglement", "qubit", "electron", "particle", "schrodinger"],
            "physics-thermodynamics": ["temperature", "heat", "entropy", "thermal", "thermo", "pressure", "enthalpy"],
            "physics-astrophysics": ["galaxy", "star", "solar", "astronomy", "cosmic", "telescope", "flare", "orbit", "planet", "space"]
        }
    },
    "business": {
        "domain": "business",
        "subs": {
            "business-sales": ["sales", "deal", "revenue", "leads", "funnel", "crm", "order", "pipeline", "quota"],
            "business-marketing": ["campaign", "ad", "marketing", "click", "conversion", "impression", "seo", "branding", "audience"],
            "business-operations": ["supply", "logistics", "workflow", "operations", "process", "inventory", "efficiency", "procurement"],
            "business-hr": ["employee", "salary", "hiring", "talent", "attrition", "payroll", "performance", "recruitment", "workforce"]
        }
    },
    "food": {
        "domain": "food",
        "subs": {
            "food-recipes": ["recipe", "ingredient", "dish", "cook", "cuisine", "meal", "baking", "taste"],
            "food-nutrition": ["calorie", "nutrition", "protein", "vitamin", "carb", "diet", "fat", "nutrient", "healthy"],
            "food-restaurants": ["restaurant", "menu", "dining", "chef", "cafe", "table", "food service", "bar"],
            "food-agriculture": ["crop", "harvest", "soil", "agriculture", "farming", "seed", "yield", "livestock", "fertilizer"]
        }
    },
    "health": {
        "domain": "health",
        "subs": {
            "health-clinical": ["clinical", "trial", "patient", "disease", "treatment", "hospital", "diagnosis", "medical", "doctor"],
            "health-genomics": ["gene", "dna", "rna", "genomics", "sequencing", "mutation", "genetic", "genome"],
            "health-public-health": ["epidemic", "vaccine", "outbreak", "public health", "mortality", "infection", "prevalence"],
            "health-fitness": ["workout", "exercise", "heart rate", "steps", "fitness", "sleep", "gym", "cardio", "calories burned"]
        }
    },
    "finance": {
        "domain": "finance",
        "subs": {
            "finance-stock-market": ["stock", "equity", "nasdaq", "share", "candlestick", "dividend", "nyse", "ticker", "portfolio", "trading"],
            "finance-banking": ["bank", "loan", "mortgage", "credit", "account", "deposit", "interest rate", "debit", "atm"],
            "finance-crypto": ["bitcoin", "crypto", "ethereum", "blockchain", "token", "defi", "nft", "btc", "eth", "wallet"],
            "finance-real-estate": ["property", "estate", "housing", "rent", "realty", "tenant", "mortgage", "home value", "listing"]
        }
    },
    "environment": {
        "domain": "environment",
        "subs": {
            "environment-climate": ["climate", "weather", "temperature", "carbon", "greenhouse", "co2", "emissions", "rainfall", "forecast", "atmosphere"],
            "environment-pollution": ["pollution", "air quality", "aqi", "waste", "plastic", "toxic", "contaminant", "smog", "water quality"],
            "environment-biodiversity": ["species", "wildlife", "forest", "ecosystem", "fauna", "flora", "conservation", "habitat", "plants", "animals"]
        }
    },
    "education": {
        "domain": "education",
        "subs": {
            "education-k-12": ["school", "grade", "student", "teacher", "classroom", "curriculum", "k-12", "exam", "homework"],
            "education-higher-ed": ["university", "college", "degree", "undergraduate", "graduate", "campus", "tuition", "academic", "scholarship"],
            "education-edtech": ["e-learning", "course", "lms", "online learning", "quiz", "mooc", "tutorial", "skill", "learning platform"]
        }
    },
    "transportation": {
        "domain": "transportation",
        "subs": {
            "transportation-logistics": ["freight", "shipping", "cargo", "delivery", "fleet", "warehouse", "tracking", "container", "supply chain"],
            "transportation-autonomous-driving": ["autonomous", "lidar", "radar", "self-driving", "lane", "sensor", "vehicle", "telemetry", "adas"],
            "transportation-public-transit": ["bus", "train", "metro", "subway", "transit", "station", "commute", "passenger", "route", "railway"]
        }
    },
    "retail": {
        "domain": "retail",
        "subs": {
            "retail-e-commerce": ["ecommerce", "e-commerce", "cart", "checkout", "product", "store", "shopify", "amazon", "online shopping", "buyer"],
            "retail-inventory": ["inventory", "stock", "sku", "warehouse", "shelf", "reorder", "merchandise", "supply", "fulfillment"],
            "retail-consumer-behavior": ["shopper", "consumer", "basket", "loyalty", "purchase history", "churn", "customer", "behavior", "review", "rating"]
        }
    },
    "technology": {
        "domain": "technology",
        "subs": {
            "technology-software-engineering": ["software", "code", "github", "bug", "commit", "api", "programming", "developer", "repository", "git"],
            "technology-aiml-datasets": ["model", "training", "dataset", "annotation", "benchmark", "embedding", "neural network", "llm", "ai", "machine learning", "chess", "game", "strategy", "vision", "nlp"],
            "technology-cybersecurity": ["vulnerability", "malware", "firewall", "cyber", "attack", "exploit", "cve", "threat", "intrusion", "ransomware", "phishing"]
        }
    },
    "other": {
        "domain": "other",
        "subs": {
            "other-general": ["dataset", "data", "records", "table", "collection", "survey", "general"],
            "other-miscellaneous": ["misc", "miscellaneous", "random", "mixed", "other", "sample"]
        }
    }
}

class DeterministicMockScorer:
    @staticmethod
    def classify(
        title: str,
        description: str,
        data_type: str,
        allowed_categories: List[Dict[str, Any]],
        sample_preview: Any = None
    ) -> Tuple[GemmaClassificationOutput, bool]:
        search_text = f"{title} {description}".lower()
        
        # Add column names to search text if tabular
        if isinstance(sample_preview, dict) and "columns" in sample_preview:
            col_names = " ".join([c.get("name", "") for c in sample_preview.get("columns", [])])
            search_text += f" {col_names}".lower()

        best_domain = "other"
        best_sub = "other-general"
        highest_score = 0
        matching_tags = set()

        for domain_slug, domain_info in DOMAIN_KEYWORDS.items():
            domain_score = 0
            for sub_slug, keywords in domain_info["subs"].items():
                for kw in keywords:
                    if kw in search_text:
                        domain_score += 1
                        matching_tags.add(kw)
                        if domain_score > highest_score:
                            highest_score = domain_score
                            best_domain = domain_slug
                            best_sub = sub_slug

        # Calculate confidence based on keyword matches
        if highest_score >= 3:
            confidence = min(0.95, 0.75 + (highest_score * 0.05))
        elif highest_score >= 1:
            confidence = 0.65 + (highest_score * 0.05)
        else:
            # Low match -> other domain with lower confidence
            confidence = 0.40
            best_domain = "other"
            best_sub = "other-general"

        if not matching_tags:
            matching_tags = {"dataset", data_type, "raw-data"}

        tags = list(matching_tags)[:6]
        reasoning = f"Deterministic classification based on matched semantic domain indicators in {data_type} title and metadata."

        output = GemmaClassificationOutput(
            primary_category=best_domain,
            subcategory=best_sub,
            secondary_categories=[],
            confidence=round(confidence, 2),
            tags=tags,
            reasoning=reasoning,
            suggested_new_category=None
        )
        return output, False

    @staticmethod
    def score(
        title: str,
        description: str,
        data_type: str,
        category_slug: str,
        precheck_metrics: Dict[str, Any],
        sample_preview: Any = None
    ) -> Tuple[GemmaScoringOutput, bool]:
        # 1. Quality Component
        quality = 85.0
        if data_type == "image":
            width = precheck_metrics.get("width", 0)
            height = precheck_metrics.get("height", 0)
            if width >= 1000 and height >= 1000:
                quality = 94.0
            elif width >= 500:
                quality = 88.0
            else:
                quality = 75.0
        else: # tabular
            schema = precheck_metrics.get("column_schema") or {}
            dup_ratio = schema.get("duplicate_row_ratio", 0.0)
            row_count = precheck_metrics.get("row_count", 0)
            # High row count and low duplicates boost quality
            if dup_ratio < 0.05 and row_count > 100:
                quality = 92.0
            elif dup_ratio < 0.15:
                quality = 84.0
            else:
                quality = 70.0

        # 2. Authenticity Component
        authenticity = 90.0
        if data_type == "image":
            if precheck_metrics.get("exif_stripped"):
                authenticity = 92.0
        else:
            # Check implausible values or duplicates
            if precheck_metrics.get("content_hash"):
                authenticity = 93.0

        # 3. Metadata Accuracy Component
        # Description length and title relevance
        desc_words = len(description.split())
        if desc_words >= 15:
            metadata_accuracy = 92.0
        elif desc_words >= 5:
            metadata_accuracy = 85.0
        else:
            metadata_accuracy = 65.0

        explanation = f"Dataset exhibits solid {data_type} structure with high signal-to-noise ratio and clean pre-check validation."
        tips = [
            "Provide detailed column descriptors or label dictionaries to further improve discovery.",
            "Maintain comprehensive documentation and versioning notes for buyers."
        ]
        if metadata_accuracy < 80.0:
            tips.append("Expand the dataset description with collection methodology to improve metadata score.")

        output = GemmaScoringOutput(
            quality=round(quality, 1),
            authenticity=round(authenticity, 1),
            metadata_accuracy=round(metadata_accuracy, 1),
            explanation=explanation,
            tips=tips[:3]
        )
        return output, False
