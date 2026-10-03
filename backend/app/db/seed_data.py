import io
import os
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.db.init_db import init_db
from app.models.user import User, UserRole, UserStatus, ContributorProfile, AgencyProfile
from app.models.category import Category
from app.models.upload import Upload, UploadFile, UploadStatus, CategorySource, DataType
from app.models.listing import Listing, ListingStatus
from app.models.ai import AIAnalysis
from app.models.order import Order, OrderStatus, License
from app.models.ledger import Wallet, LedgerEntry, PayoutRequest, AccountType, EntryDirection, EntryKind, PayoutStatus
from app.models.audit import Flag, FlagStatus, AuditLog, DownloadLog
from app.services.storage import get_storage_service
from app.services.pricing import calculate_suggested_price
from app.services.payment.payment_service import process_payment_webhook_event

def create_seed_image(color=(50, 100, 200), title="DATASET PREVIEW") -> bytes:
    img = Image.new("RGB", (640, 480), color=color)
    draw = ImageDraw.Draw(img)
    # Draw geometric patterns
    for i in range(10, 600, 40):
        draw.line([(i, 0), (i + 40, 480)], fill=(255, 255, 255, 60), width=2)
    draw.rectangle([40, 40, 600, 440], outline=(255, 255, 255), width=3)
    draw.text((60, 220), title, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

DATASET_DEFINITIONS = [
    # --- PHYSICS ---
    {
        "domain": "physics",
        "sub": "physics-quantum",
        "type": "tabular",
        "title": "Quantum Spin Particle Entanglement Telemetry",
        "description": "High-precision qubit entanglement measurements across superconducting circuits with state fidelity.",
        "tags": ["quantum", "spin", "physics", "qubit", "telemetry"],
        "price_paise": 650000,
        "score": 96.0,
        "df": pd.DataFrame({
            "qubit_id": [1, 2, 3, 4, 5, 6, 7, 8],
            "state_fidelity": [0.994, 0.989, 0.998, 0.985, 0.992, 0.978, 0.995, 0.991],
            "decoherence_time_us": [124.5, 118.2, 132.0, 110.4, 128.6, 105.3, 130.1, 122.8],
            "gate_error_rate": [0.0012, 0.0021, 0.0008, 0.0029, 0.0015, 0.0035, 0.0010, 0.0018]
        })
    },
    {
        "domain": "physics",
        "sub": "physics-astrophysics",
        "type": "image",
        "title": "Solar Flare Coronal Mass Ejection Spectrum",
        "description": "Multi-wavelength extreme ultraviolet solar flare coronagraph image dataset.",
        "tags": ["solar", "astrophysics", "telescope", "cosmic", "flare"],
        "price_paise": 550000,
        "score": 93.0,
        "color": (230, 90, 40)
    },
    {
        "domain": "physics",
        "sub": "physics-mechanics",
        "type": "tabular",
        "title": "Hypersonic Wind Tunnel Aerodynamic Drag Telemetry",
        "description": "Mach 5.5 boundary layer shockwave measurements and pressure sensor grids.",
        "tags": ["aerodynamics", "mechanics", "sensor", "velocity", "physics"],
        "price_paise": 480000,
        "score": 91.0,
        "df": pd.DataFrame({
            "mach_number": [5.2, 5.4, 5.5, 5.6, 5.8],
            "reynolds_number": [1.2e6, 1.4e6, 1.5e6, 1.6e6, 1.8e6],
            "drag_coefficient": [0.034, 0.036, 0.038, 0.041, 0.045],
            "stagnation_temp_k": [1450, 1520, 1580, 1640, 1720]
        })
    },

    # --- BUSINESS ---
    {
        "domain": "business",
        "sub": "business-sales",
        "type": "tabular",
        "title": "Enterprise B2B SaaS Sales Pipeline and ACV Velocity",
        "description": "Quarterly CRM sales deals, stage conversion rates, discount margins, and annual contract value.",
        "tags": ["sales", "crm", "revenue", "deals", "b2b"],
        "price_paise": 420000,
        "score": 88.0,
        "df": pd.DataFrame({
            "deal_id": [201, 202, 203, 204, 205],
            "acv_usd": [45000, 120000, 85000, 250000, 60000],
            "sales_cycle_days": [45, 92, 60, 120, 38],
            "win_probability": [0.85, 0.65, 0.75, 0.50, 0.90],
            "discount_pct": [0.05, 0.12, 0.08, 0.15, 0.03]
        })
    },
    {
        "domain": "business",
        "sub": "business-marketing",
        "type": "tabular",
        "title": "Multi-Touch Omnichannel Ad Conversion Funnel",
        "description": "Cross-channel attribution data spanning search, social ads, programmatic display, and email funnels.",
        "tags": ["marketing", "ad", "conversion", "campaign", "funnel"],
        "price_paise": 380000,
        "score": 87.0,
        "df": pd.DataFrame({
            "campaign_id": [11, 12, 13, 14, 15],
            "ad_spend_usd": [12000, 25000, 8000, 45000, 18000],
            "roas": [3.4, 4.1, 2.8, 4.8, 3.9],
            "cpa_usd": [24.5, 18.2, 32.0, 15.4, 21.6],
            "attribution_model": ["data_driven", "w_shaped", "linear", "time_decay", "first_touch"]
        })
    },
    {
        "domain": "business",
        "sub": "business-operations",
        "type": "tabular",
        "title": "Global Air Cargo Supply Chain Freight Transit Timings",
        "description": "Port dwell times, customs clearance latencies, and air freight temperature telemetry.",
        "tags": ["operations", "logistics", "supply", "freight", "workflow"],
        "price_paise": 450000,
        "score": 89.0,
        "df": pd.DataFrame({
            "route_code": ["ORD-FRA", "HKG-LAX", "SIN-LHR", "NRT-JFK", "DXB-SYD"],
            "dwell_hours": [4.2, 6.8, 3.5, 5.1, 4.9],
            "clearance_sla_met": [True, True, True, False, True],
            "temp_excursion_count": [0, 0, 1, 0, 0]
        })
    },

    # --- HEALTH ---
    {
        "domain": "health",
        "sub": "health-genomics",
        "type": "tabular",
        "title": "Rare Oncogene Variant Mutation Frequency Database",
        "description": "Targeted next-generation genomic sequencing variants across cancer clinical cohorts.",
        "tags": ["genomics", "dna", "gene", "mutation", "clinical"],
        "price_paise": 850000,
        "score": 97.0,
        "df": pd.DataFrame({
            "gene_symbol": ["TP53", "KRAS", "EGFR", "BRCA1", "PIK3CA", "BRAF"],
            "variant_allele_freq": [0.42, 0.38, 0.55, 0.28, 0.49, 0.61],
            "pathogenicity_score": [0.98, 0.95, 0.99, 0.94, 0.91, 0.99],
            "cohort_size": [1200, 1200, 1200, 1200, 1200, 1200]
        })
    },
    {
        "domain": "health",
        "sub": "health-clinical",
        "type": "image",
        "title": "Microscopic Cellular Histopathology Stains",
        "description": "High-resolution 40x whole slide histology tissue scans with annotated cellular boundaries.",
        "tags": ["clinical", "histology", "microscope", "cell", "health"],
        "price_paise": 720000,
        "score": 94.0,
        "color": (160, 40, 130)
    },
    {
        "domain": "health",
        "sub": "health-fitness",
        "type": "tabular",
        "title": "Continuous Optical Heart Rate & VO2 Max Sensor Log",
        "description": "High-frequency PPG wearable telemetry tracking heart rate variability and aerobic performance.",
        "tags": ["fitness", "heart", "hrv", "wearable", "health"],
        "price_paise": 320000,
        "score": 86.0,
        "df": pd.DataFrame({
            "user_index": [101, 102, 103, 104, 105],
            "resting_hr_bpm": [54, 62, 58, 68, 51],
            "vo2_max_ml_kg": [52.4, 44.1, 48.9, 39.8, 56.2],
            "sleep_efficiency_pct": [92, 86, 89, 78, 95]
        })
    },

    # --- FINANCE ---
    {
        "domain": "finance",
        "sub": "finance-stock-market",
        "type": "tabular",
        "title": "High-Frequency Limit Order Book Depth & Microstructure",
        "description": "Level-2 tick data showing bid-ask spreads, order book imbalance, and execution latencies.",
        "tags": ["stock", "equity", "market", "nasdaq", "finance"],
        "price_paise": 780000,
        "score": 95.0,
        "df": pd.DataFrame({
            "timestamp_ms": [1700000000100, 1700000000200, 1700000000300, 1700000000400],
            "bid_price": [182.45, 182.46, 182.45, 182.48],
            "ask_price": [182.47, 182.48, 182.47, 182.50],
            "spread_bps": [1.09, 1.09, 1.09, 1.09],
            "order_imbalance": [0.24, -0.15, 0.08, 0.42]
        })
    },
    {
        "domain": "finance",
        "sub": "finance-crypto",
        "type": "tabular",
        "title": "DEX Automated Market Maker Liquidity Pool Slippage",
        "description": "Constant-product AMM swap volumes, impermanent loss coefficients, and gas fee variations.",
        "tags": ["crypto", "defi", "blockchain", "ethereum", "token"],
        "price_paise": 620000,
        "score": 90.0,
        "df": pd.DataFrame({
            "pool_pair": ["ETH-USDC", "WBTC-ETH", "UNI-ETH", "LINK-USDC"],
            "tvl_usd": [245000000, 180000000, 45000000, 32000000],
            "volume_24h_usd": [85000000, 62000000, 12000000, 9500000],
            "avg_slippage_pct": [0.0004, 0.0006, 0.0018, 0.0022]
        })
    },
    {
        "domain": "finance",
        "sub": "finance-real-estate",
        "type": "tabular",
        "title": "Commercial Real Estate Cap Rates & Net Operating Income",
        "description": "Multi-family and industrial REIT property asset appraisals across top 20 metropolitan areas.",
        "tags": ["real-estate", "property", "realty", "rent", "housing"],
        "price_paise": 680000,
        "score": 92.0,
        "df": pd.DataFrame({
            "asset_id": ["IND-001", "MF-102", "OFF-304", "RET-501"],
            "cap_rate_pct": [5.4, 4.8, 6.9, 7.2],
            "noi_usd": [1200000, 850000, 2100000, 950000],
            "occupancy_rate": [0.98, 0.95, 0.82, 0.88]
        })
    },

    # --- TECHNOLOGY ---
    {
        "domain": "technology",
        "sub": "technology-software-engineering",
        "type": "tabular",
        "title": "Open Source Software Engineering Commit Velocity",
        "description": "Code review cycle durations, CI/CD test failure frequencies, and developer pull request throughput.",
        "tags": ["software", "code", "github", "commit", "api"],
        "price_paise": 580000,
        "score": 91.0,
        "df": pd.DataFrame({
            "repo_id": ["k8s", "react", "fastapi", "pandas", "pytorch"],
            "pr_merge_hours": [18.5, 12.4, 8.2, 24.1, 14.8],
            "ci_pass_rate": [0.94, 0.98, 0.96, 0.92, 0.95],
            "active_reviewers": [45, 28, 12, 34, 62]
        })
    },
    {
        "domain": "technology",
        "sub": "technology-aiml-datasets",
        "type": "image",
        "title": "Synthetic Optical Character Recognition Invoices",
        "description": "Bespoke multilingual invoice template images with pixel-exact bounding box labels.",
        "tags": ["model", "training", "dataset", "annotation", "benchmark"],
        "price_paise": 740000,
        "score": 95.0,
        "color": (40, 140, 180)
    },
    {
        "domain": "technology",
        "sub": "technology-cybersecurity",
        "type": "tabular",
        "title": "Network Intrusion Detection & Zero-Day Packet Flows",
        "description": "DDoS packet distributions, SYN flood indicators, and malicious port scan netflow logs.",
        "tags": ["cybersecurity", "vulnerability", "malware", "cyber", "attack"],
        "price_paise": 690000,
        "score": 93.0,
        "df": pd.DataFrame({
            "flow_duration_ms": [120, 450, 12, 2800, 55],
            "packet_count": [1200, 5400, 60, 24000, 450],
            "syn_flag_ratio": [0.98, 0.12, 0.05, 0.99, 0.02],
            "threat_label": ["syn_flood", "normal", "normal", "ddos_amp", "normal"]
        })
    },

    # --- ENVIRONMENT ---
    {
        "domain": "environment",
        "sub": "environment-climate",
        "type": "tabular",
        "title": "Atmospheric Greenhouse Gas Concentrations and Heat Index",
        "description": "Tropospheric CO2, methane, and particulate matter PPM measurements from sensor buoys.",
        "tags": ["climate", "environment", "co2", "weather", "atmosphere"],
        "price_paise": 480000,
        "score": 92.0,
        "df": pd.DataFrame({
            "station_id": ["MLO-01", "SPO-02", "BRW-03", "THD-04"],
            "co2_ppm": [422.4, 419.8, 425.1, 421.9],
            "ch4_ppb": [1912, 1880, 1945, 1905],
            "ambient_temp_c": [14.2, -28.4, -4.2, 18.5]
        })
    },
    {
        "domain": "environment",
        "sub": "environment-biodiversity",
        "type": "image",
        "title": "Satellite Rainforest Canopy Deforestation Multi-Spectral",
        "description": "Sentinel-2 satellite imagery of Amazonian rainforest vegetation indices (NDVI).",
        "tags": ["biodiversity", "satellite", "canopy", "forest", "environment"],
        "price_paise": 520000,
        "score": 90.0,
        "color": (30, 120, 60)
    },

    # --- FOOD & AGRICULTURE ---
    {
        "domain": "food",
        "sub": "food-agriculture",
        "type": "tabular",
        "title": "Precision Soil Nitrogen, Phosphorus & Moisture Grid",
        "description": "Autonomous tractor telemetry and drone hyperspectral crop nutrient telemetry.",
        "tags": ["agriculture", "soil", "crop", "farming", "harvest"],
        "price_paise": 380000,
        "score": 88.0,
        "df": pd.DataFrame({
            "plot_id": ["A-101", "A-102", "B-201", "B-202", "C-301"],
            "soil_moisture_pct": [28.4, 31.2, 19.8, 24.5, 33.1],
            "nitrogen_ppm": [45, 52, 38, 41, 58],
            "projected_yield_bushels": [195, 210, 160, 178, 225]
        })
    },
    {
        "domain": "food",
        "sub": "food-nutrition",
        "type": "image",
        "title": "Culinary Plated Meal Macronutrient Composition",
        "description": "Annotated photographic dataset of balanced restaurant dishes with verified calorie breakdowns.",
        "tags": ["food", "nutrition", "meal", "calorie", "diet"],
        "price_paise": 310000,
        "score": 86.0,
        "color": (210, 140, 50)
    },

    # --- TRANSPORTATION ---
    {
        "domain": "transportation",
        "sub": "transportation-autonomous-driving",
        "type": "image",
        "title": "Autonomous Lidar Point Cloud Road Surface Obstacles",
        "description": "3D annotated automotive lidar point clouds with semantic road segmentation.",
        "tags": ["autonomous", "driving", "transportation", "lidar", "vehicle"],
        "price_paise": 790000,
        "score": 96.0,
        "color": (70, 70, 110)
    },
    {
        "domain": "transportation",
        "sub": "transportation-logistics",
        "type": "tabular",
        "title": "Urban Metro Transit Tap-In Peak Flow and Congestion",
        "description": "Smart transit card turnstile ingress and egress frequencies across subway lines.",
        "tags": ["logistics", "transit", "transportation", "urban", "traffic"],
        "price_paise": 460000,
        "score": 89.0,
        "df": pd.DataFrame({
            "station_code": ["ST-01", "ST-02", "ST-03", "ST-04", "ST-05"],
            "hourly_tap_ins": [14200, 8900, 22400, 6100, 18500],
            "dwell_seconds": [35, 28, 45, 22, 40],
            "capacity_utilization": [0.92, 0.74, 0.98, 0.55, 0.94]
        })
    },
    {
        "domain": "transportation",
        "sub": "transportation-autonomous-driving",
        "type": "tabular",
        "title": "Electric Vehicle Battery Degradation & Thermal Cycles",
        "description": "Lithium-ion cell voltage curves, fast-charge thermal cycles, and state-of-health degradation.",
        "tags": ["battery", "ev", "autonomous", "vehicle", "transportation"],
        "price_paise": 510000,
        "score": 90.0,
        "df": pd.DataFrame({
            "cell_id": ["NMC-01", "NMC-02", "LFP-01", "LFP-02"],
            "cycle_count": [850, 1200, 2400, 3100],
            "state_of_health_pct": [91.2, 85.4, 94.8, 91.0],
            "internal_resistance_mohm": [1.45, 1.82, 1.12, 1.34]
        })
    },

    # --- RETAIL ---
    {
        "domain": "retail",
        "sub": "retail-e-commerce",
        "type": "tabular",
        "title": "E-Commerce Cart Abandonment & Lifetime Value Cohorts",
        "description": "Session clickstream data, checkout step drop-off rates, and 12-month repeat purchase cohorts.",
        "tags": ["retail", "ecommerce", "consumer", "inventory", "sales"],
        "price_paise": 420000,
        "score": 88.0,
        "df": pd.DataFrame({
            "cohort_month": ["2025-01", "2025-02", "2025-03", "2025-04"],
            "acquisition_cac_usd": [42.5, 38.0, 45.2, 41.0],
            "ltv_12m_usd": [185.0, 192.4, 178.0, 204.5],
            "cart_abandon_rate": [0.68, 0.65, 0.71, 0.63]
        })
    },
    {
        "domain": "retail",
        "sub": "retail-inventory",
        "type": "image",
        "title": "Supermarket Shelf Product Placement & Planogram",
        "description": "Overhead grocery aisle shelf product bounding boxes for stockout detection.",
        "tags": ["retail", "inventory", "shelf", "supermarket", "image"],
        "price_paise": 440000,
        "score": 89.0,
        "color": (200, 60, 90)
    },

    # --- EDUCATION ---
    {
        "domain": "education",
        "sub": "education-edtech",
        "type": "tabular",
        "title": "Adaptive Learning Platform Step Latency & Mastery Curves",
        "description": "Student math problem attempt timestamps, hint request frequencies, and concept mastery.",
        "tags": ["education", "edtech", "learning", "student", "mastery"],
        "price_paise": 340000,
        "score": 87.0,
        "df": pd.DataFrame({
            "student_id": [501, 502, 503, 504, 505],
            "concept_mastery_pct": [88, 94, 76, 82, 91],
            "avg_step_latency_sec": [14.2, 9.8, 22.4, 17.5, 11.0],
            "hints_used_count": [2, 0, 5, 3, 1]
        })
    },
    {
        "domain": "education",
        "sub": "education-higher-ed",
        "type": "tabular",
        "title": "University Engineering Course Completion & Retention",
        "description": "Prerequisite grade correlations, lab attendance rates, and degree graduation trajectories.",
        "tags": ["education", "higher-ed", "university", "stem", "retention"],
        "price_paise": 370000,
        "score": 89.0,
        "df": pd.DataFrame({
            "cohort_year": [2021, 2022, 2023, 2024],
            "enrolled_students": [450, 480, 520, 550],
            "retention_rate_yr2": [0.89, 0.91, 0.92, 0.94],
            "avg_gpa": [3.42, 3.48, 3.51, 3.55]
        })
    },

    # --- OTHER / MISC ---
    {
        "domain": "other",
        "sub": "other-general",
        "type": "tabular",
        "title": "Global Seismic Activity & Earthquake Richter Magnitude",
        "description": "Geological tectonic plate sensor accelerations and epicenter coordinates.",
        "tags": ["seismic", "earthquake", "geology", "sensor", "other"],
        "price_paise": 220000,
        "score": 85.0,
        "df": pd.DataFrame({
            "event_id": ["EQ-1001", "EQ-1002", "EQ-1003", "EQ-1004"],
            "richter_magnitude": [4.2, 5.8, 3.1, 6.4],
            "depth_km": [12.4, 8.1, 24.5, 6.2],
            "aftershock_count": [4, 18, 1, 32]
        })
    }
]

def seed_database(db: Session) -> None:
    print(" [1/5] Ensuring Database Tables & Taxonomy Tree...")
    Base.metadata.create_all(bind=engine)
    init_db(db)

    print(" [2/5] Creating Core Seed Users (Admin, Contributors, Agencies)...")
    admin_user = db.query(User).filter(User.email == "admin@reactndata.com").first()
    if not admin_user:
        admin_user = User(
            email="admin@reactndata.com",
            password_hash=get_password_hash("password123"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE
        )
        db.add(admin_user)
        db.flush()

    contributors = []
    contributor_configs = [
        ("alice.physicist@quantumlab.io", "Dr. Alice Physicist", 98.0),
        ("marcus.bio@genomicscore.org", "Marcus Genomics Lab", 96.0),
        ("sarah.fin@marketpulse.ai", "Sarah Finance AI", 94.0),
        ("elena.ai@cvbenchmarks.io", "Elena Computer Vision", 95.0),
        ("chen.agri@ecoglobal.org", "Chen Agricultural Data", 92.0),
    ]

    for email, name, rep in contributor_configs:
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(
                email=email,
                password_hash=get_password_hash("password123"),
                role=UserRole.CONTRIBUTOR,
                status=UserStatus.ACTIVE
            )
            db.add(u)
            db.flush()
            prof = ContributorProfile(user_id=u.id, display_name=name, reputation_score=rep)
            wallet = Wallet(user_id=u.id, pending_balance_paise=0, available_balance_paise=0)
            db.add(prof)
            db.add(wallet)
            db.flush()
        contributors.append(u)

    agencies = []
    agency_configs = [
        ("buyer@deepmindventures.com", "DeepMind Ventures"),
        ("acquisitions@automotiveai.com", "Apex Mobility Systems"),
        ("data-buyer@fintechcap.com", "Horizon Capital Fund"),
    ]

    for email, comp in agency_configs:
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(
                email=email,
                password_hash=get_password_hash("password123"),
                role=UserRole.AGENCY,
                status=UserStatus.ACTIVE
            )
            db.add(u)
            db.flush()
            prof = AgencyProfile(user_id=u.id, company_name=comp)
            db.add(prof)
            db.flush()
        agencies.append(u)

    db.commit()

    print(f" [3/5] Seeding {len(DATASET_DEFINITIONS)} Realistic Multi-Domain Datasets...")
    storage = get_storage_service()
    published_listings: List[Listing] = []

    for idx, d in enumerate(DATASET_DEFINITIONS):
        # Assign contributor round-robin
        contrib = contributors[idx % len(contributors)]

        # Find category and subcategory
        cat = db.query(Category).filter(Category.slug == d["domain"]).first()
        sub = db.query(Category).filter(Category.slug == d["sub"]).first() if "sub" in d else None

        category_id = cat.id if cat else None
        subcategory_id = sub.id if sub else None

        # Check if already exists
        existing_upload = db.query(Upload).filter(Upload.title == d["title"]).first()
        if existing_upload:
            if existing_upload.listing:
                published_listings.append(existing_upload.listing)
            continue

        now = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))

        # 1. Create Upload record
        upload = Upload(
            contributor_id=contrib.id,
            title=d["title"],
            description=d["description"],
            status=UploadStatus.PUBLISHED,
            category_id=category_id,
            subcategory_id=subcategory_id,
            category_source=CategorySource.AI,
            category_confidence=0.92,
            tags=d["tags"],
            price_paise=d["price_paise"],
            ai_min_price=int(d["price_paise"] * 0.8),
            ai_max_price=int(d["price_paise"] * 1.3),
            ai_training_allowed=True,
            consent_version="1.0",
            consent_at=now,
            created_at=now
        )
        db.add(upload)
        db.flush()

        # 2. Store binary payload and file metadata
        if d["type"] == "tabular":
            df = d.get("df", pd.DataFrame({"id": [1, 2, 3], "value": [10, 20, 30]}))
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            storage_key = f"uploads/{upload.id}/data.csv"
            storage.save_file(csv_bytes, storage_key)

            upload_file = UploadFile(
                upload_id=upload.id,
                data_type=DataType.TABULAR,
                storage_key=storage_key,
                preview_key=None,
                mime="text/csv",
                size=len(csv_bytes),
                row_count=len(df),
                column_schema={"columns": [{"name": col, "type": str(df[col].dtype)} for col in df.columns]},
                content_hash=f"hash_{upload.id}",
                signature_hash=f"sig_{upload.id}",
                created_at=now
            )
        else:
            img_bytes = create_seed_image(color=d.get("color", (40, 90, 180)), title=d["title"])
            storage_key = f"uploads/{upload.id}/image.png"
            preview_key = f"previews/{upload.id}/preview.png"
            storage.save_file(img_bytes, storage_key)
            storage.save_file(img_bytes, preview_key)

            upload_file = UploadFile(
                upload_id=upload.id,
                data_type=DataType.IMAGE,
                storage_key=storage_key,
                preview_key=preview_key,
                mime="image/png",
                size=len(img_bytes),
                width=640,
                height=480,
                phash="9f8e7d6c5b4a3a2b",
                exif_stripped=True,
                created_at=now
            )

        db.add(upload_file)

        # 3. Create AI Analysis record
        score = d.get("score", 90.0)
        ai_analysis = AIAnalysis(
            upload_id=upload.id,
            model_name="gemma-2-9b-it",
            config_version="1.0.0",
            taxonomy_version=1,
            classification_output={
                "primary_category": d["domain"],
                "subcategory": d.get("sub"),
                "confidence": 0.94,
                "tags": d["tags"],
                "reasoning": "High-confidence domain alignment confirmed with multi-spectral signal analysis."
            },
            quality=score,
            authenticity=score + 2 if score < 98 else 99,
            uniqueness=score - 2,
            metadata_accuracy=95.0,
            reputation=96.0,
            total_score=score,
            explanation=f"Exhibits exceptional signal-to-noise ratio, verified schemas, and rigorous pre-check validation.",
            tips=["Maintain comprehensive column descriptor notes for prospective agency buyers."],
            degraded=False,
            created_at=now
        )
        db.add(ai_analysis)

        # 4. Create active Marketplace Listing
        listing = Listing(
            upload_id=upload.id,
            status=ListingStatus.ACTIVE,
            published_at=now,
            created_at=now
        )
        db.add(listing)
        db.flush()
        published_listings.append(listing)

    db.commit()

    print(" [4/5] Simulating Marketplace Transactions, 80/20 Splits, Licenses & Wallet Credits...")
    # Seed 6 paid orders
    for i in range(min(8, len(published_listings))):
        target_listing = published_listings[i]
        buyer = agencies[i % len(agencies)]

        # Prevent duplicate
        existing_order = db.query(Order).filter(Order.listing_id == target_listing.id, Order.buyer_id == buyer.id).first()
        if not existing_order:
            order = Order(
                buyer_id=buyer.id,
                listing_id=target_listing.id,
                amount_paise=target_listing.upload.price_paise,
                status=OrderStatus.AWAITING_PAYMENT,
                created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 10))
            )
            db.add(order)
            db.commit()
            db.refresh(order)

            # Process payment simulation (80/20 double entry ledger + license + wallet)
            process_payment_webhook_event(
                db=db,
                order_id=order.id,
                event_status="paid",
                provider_ref=f"seed_mock_pay_{order.id}",
                raw_payload={"seed": True}
            )

    print(" [5/5] Seeding Sample Payout Requests and Admin Audit Logs...")
    # Seed a sample payout for contributor 0
    c0 = contributors[0]
    wallet0 = db.query(Wallet).filter(Wallet.user_id == c0.id).first()
    if wallet0 and wallet0.available_balance_paise >= 10000:
        payout = PayoutRequest(
            user_id=c0.id,
            amount_paise=10000,
            status=PayoutStatus.COMPLETED,
            method="bank_transfer",
            destination="HDFC0001234 - 501004829102",
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
            processed_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        db.add(payout)
        wallet0.available_balance_paise -= 10000
        db.commit()

    # System seed log
    db.add(AuditLog(
        actor_id=admin_user.id,
        action="MARKETPLACE_SEEDED",
        entity="system",
        entity_id="1",
        meta={"datasets_count": len(DATASET_DEFINITIONS), "listings_count": len(published_listings)}
    ))
    db.commit()

    print(f" SUCCESS: Seeded {len(DATASET_DEFINITIONS)} multi-domain datasets, 3 agencies, 5 contributors, paid orders, and active listings!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
