from typing import Dict, Any

AI_CONFIG_VERSION = "1.0"

# Trust Score Component Weights (Must sum to 1.0)
TRUST_SCORE_WEIGHTS = {
    "quality": 0.25,
    "authenticity": 0.30,
    "uniqueness": 0.20,
    "metadata_accuracy": 0.15,
    "reputation": 0.10
}

# Classification Confidence Thresholds
CONFIDENCE_AUTO_ASSIGN_THRESHOLD = 0.75
CONFIDENCE_REVIEW_THRESHOLD = 0.50

# Pricing Configuration
# Price = Category Base Price * Trust Factor * Demand Factor
# Trust Factor Piecewise Function:
# Score < 40  -> 0.5
# Score 40-70 -> 0.5 + ((Score - 40) / 30) * 0.5  (ranges 0.5 to 1.0)
# Score > 70  -> 1.0 + ((Score - 70) / 30) * 0.6  (ranges 1.0 to 1.6)
PRICE_MIN_RATIO = 0.80  # AI Min Price = 80% of suggested price
PRICE_MAX_RATIO = 1.30  # AI Max Price = 130% of suggested price
