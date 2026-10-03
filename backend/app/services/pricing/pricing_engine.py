import math
from typing import Dict, Any
from app.core.ai_config import PRICE_MIN_RATIO, PRICE_MAX_RATIO

def calculate_trust_factor(trust_score: float) -> float:
    """
    Piecewise trust score factor function:
    - Score < 40  -> 0.5
    - Score 40-70 -> linear from 0.5 to 1.0
    - Score > 70  -> linear from 1.0 to 1.6
    """
    clamped_score = max(0.0, min(100.0, float(trust_score)))
    if clamped_score < 40.0:
        return 0.5
    elif clamped_score <= 70.0:
        return 0.5 + ((clamped_score - 40.0) / 30.0) * 0.5
    else:
        return 1.0 + ((clamped_score - 70.0) / 30.0) * 0.6

def get_demand_factor(category_slug: str = "") -> float:
    """
    Hook for dynamic demand factor based on marketplace search and purchase activity.
    Returns 1.0 for the MVP.
    """
    return 1.0

def calculate_suggested_price(
    base_price_paise: int,
    trust_score: float,
    demand_factor: float = 1.0
) -> Dict[str, int]:
    """
    Calculates the AI proposed price and suggested min-max range in integer paise.
    price = category_base_price * trust_score_factor * demand_factor
    """
    trust_factor = calculate_trust_factor(trust_score)
    computed_price = base_price_paise * trust_factor * demand_factor
    
    suggested_price_paise = int(math.floor(computed_price))
    ai_min_price_paise = int(math.floor(suggested_price_paise * PRICE_MIN_RATIO))
    ai_max_price_paise = int(math.ceil(suggested_price_paise * PRICE_MAX_RATIO))

    # Ensure min price is at least 1000 paise ($10/₹10)
    ai_min_price_paise = max(1000, ai_min_price_paise)
    suggested_price_paise = max(ai_min_price_paise, suggested_price_paise)
    ai_max_price_paise = max(suggested_price_paise, ai_max_price_paise)

    return {
        "suggested_price_paise": suggested_price_paise,
        "ai_min_price_paise": ai_min_price_paise,
        "ai_max_price_paise": ai_max_price_paise,
        "trust_factor": round(trust_factor, 3),
        "demand_factor": round(demand_factor, 3)
    }
