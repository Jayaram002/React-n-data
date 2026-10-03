from sqlalchemy.orm import Session
from app.models.category import Category
from app.core.database import engine
from app.db.base import Base

SEED_TAXONOMY = [
    {
        "name": "Physics",
        "slug": "physics",
        "base_price_paise": 500000,
        "subcategories": [
            {"name": "Mechanics", "slug": "physics-mechanics", "base_price_paise": 500000},
            {"name": "Optics", "slug": "physics-optics", "base_price_paise": 500000},
            {"name": "Quantum", "slug": "physics-quantum", "base_price_paise": 750000},
            {"name": "Thermodynamics", "slug": "physics-thermodynamics", "base_price_paise": 500000},
            {"name": "Astrophysics", "slug": "physics-astrophysics", "base_price_paise": 600000},
        ]
    },
    {
        "name": "Business",
        "slug": "business",
        "base_price_paise": 400000,
        "subcategories": [
            {"name": "Sales", "slug": "business-sales", "base_price_paise": 400000},
            {"name": "Marketing", "slug": "business-marketing", "base_price_paise": 400000},
            {"name": "Operations", "slug": "business-operations", "base_price_paise": 400000},
            {"name": "HR", "slug": "business-hr", "base_price_paise": 350000},
        ]
    },
    {
        "name": "Food",
        "slug": "food",
        "base_price_paise": 300000,
        "subcategories": [
            {"name": "Recipes", "slug": "food-recipes", "base_price_paise": 250000},
            {"name": "Nutrition", "slug": "food-nutrition", "base_price_paise": 300000},
            {"name": "Restaurants", "slug": "food-restaurants", "base_price_paise": 350000},
            {"name": "Agriculture", "slug": "food-agriculture", "base_price_paise": 400000},
        ]
    },
    {
        "name": "Health",
        "slug": "health",
        "base_price_paise": 600000,
        "subcategories": [
            {"name": "Clinical", "slug": "health-clinical", "base_price_paise": 700000},
            {"name": "Genomics", "slug": "health-genomics", "base_price_paise": 900000},
            {"name": "Public Health", "slug": "health-public-health", "base_price_paise": 500000},
            {"name": "Fitness", "slug": "health-fitness", "base_price_paise": 350000},
        ]
    },
    {
        "name": "Finance",
        "slug": "finance",
        "base_price_paise": 700000,
        "subcategories": [
            {"name": "Stock Market", "slug": "finance-stock-market", "base_price_paise": 800000},
            {"name": "Banking", "slug": "finance-banking", "base_price_paise": 750000},
            {"name": "Crypto", "slug": "finance-crypto", "base_price_paise": 650000},
            {"name": "Real Estate", "slug": "finance-real-estate", "base_price_paise": 700000},
        ]
    },
    {
        "name": "Environment",
        "slug": "environment",
        "base_price_paise": 450000,
        "subcategories": [
            {"name": "Climate", "slug": "environment-climate", "base_price_paise": 500000},
            {"name": "Pollution", "slug": "environment-pollution", "base_price_paise": 400000},
            {"name": "Biodiversity", "slug": "environment-biodiversity", "base_price_paise": 450000},
        ]
    },
    {
        "name": "Education",
        "slug": "education",
        "base_price_paise": 350000,
        "subcategories": [
            {"name": "K-12", "slug": "education-k-12", "base_price_paise": 300000},
            {"name": "Higher Ed", "slug": "education-higher-ed", "base_price_paise": 400000},
            {"name": "EdTech", "slug": "education-edtech", "base_price_paise": 350000},
        ]
    },
    {
        "name": "Transportation",
        "slug": "transportation",
        "base_price_paise": 500000,
        "subcategories": [
            {"name": "Logistics", "slug": "transportation-logistics", "base_price_paise": 500000},
            {"name": "Autonomous Driving", "slug": "transportation-autonomous-driving", "base_price_paise": 800000},
            {"name": "Public Transit", "slug": "transportation-public-transit", "base_price_paise": 400000},
        ]
    },
    {
        "name": "Retail",
        "slug": "retail",
        "base_price_paise": 400000,
        "subcategories": [
            {"name": "E-commerce", "slug": "retail-e-commerce", "base_price_paise": 450000},
            {"name": "Inventory", "slug": "retail-inventory", "base_price_paise": 400000},
            {"name": "Consumer Behavior", "slug": "retail-consumer-behavior", "base_price_paise": 400000},
        ]
    },
    {
        "name": "Technology",
        "slug": "technology",
        "base_price_paise": 600000,
        "subcategories": [
            {"name": "Software Engineering", "slug": "technology-software-engineering", "base_price_paise": 600000},
            {"name": "AI/ML Datasets", "slug": "technology-aiml-datasets", "base_price_paise": 750000},
            {"name": "Cybersecurity", "slug": "technology-cybersecurity", "base_price_paise": 700000},
        ]
    },
    {
        "name": "Other",
        "slug": "other",
        "base_price_paise": 200000,
        "subcategories": [
            {"name": "General", "slug": "other-general", "base_price_paise": 200000},
            {"name": "Miscellaneous", "slug": "other-miscellaneous", "base_price_paise": 200000},
        ]
    }
]

def init_db(db: Session) -> None:
    Base.metadata.create_all(bind=engine)
    
    # Check if categories already exist
    existing_cat = db.query(Category).first()
    if not existing_cat:
        for domain in SEED_TAXONOMY:
            parent_cat = Category(
                name=domain["name"],
                slug=domain["slug"],
                base_price_paise=domain["base_price_paise"],
                active=True,
                version=1
            )
            db.add(parent_cat)
            db.flush() # flush to get parent_cat.id
            
            for sub in domain.get("subcategories", []):
                sub_cat = Category(
                    parent_id=parent_cat.id,
                    name=sub["name"],
                    slug=sub["slug"],
                    base_price_paise=sub["base_price_paise"],
                    active=True,
                    version=1
                )
                db.add(sub_cat)
        db.commit()
