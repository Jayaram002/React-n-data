import io
import pytest
from PIL import Image
import pandas as pd
from fastapi.testclient import TestClient

from app.core.ai_config import (
    TRUST_SCORE_WEIGHTS,
    CONFIDENCE_AUTO_ASSIGN_THRESHOLD,
    CONFIDENCE_REVIEW_THRESHOLD
)
from app.services.pricing.pricing_engine import calculate_trust_factor, calculate_suggested_price

def get_auth_headers(client: TestClient, email: str, role: str = "contributor"):
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "role": role,
        "display_name": "TestContributor"
    })
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def create_dummy_image(color=(30, 80, 160), size=(120, 120)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_pricing_piecewise_curve_and_inheritance():
    # Test piecewise function
    assert calculate_trust_factor(30.0) == 0.5
    assert calculate_trust_factor(40.0) == 0.5
    assert calculate_trust_factor(70.0) == 1.0
    assert round(calculate_trust_factor(100.0), 2) == 1.60

    # Test suggested pricing formula (500000 paise = 5000 units, score 70.0 -> factor 1.0)
    pricing = calculate_suggested_price(500000, 70.0, demand_factor=1.0)
    assert pricing["suggested_price_paise"] == 500000
    assert pricing["ai_min_price_paise"] == int(500000 * 0.80)
    assert pricing["ai_max_price_paise"] == int(500000 * 1.30)

def test_ai_classification_and_trust_score(client: TestClient):
    headers = get_auth_headers(client, "physicist@university.edu", "contributor")
    
    # Upload Physics dataset with keyword hints
    df = pd.DataFrame({
        "velocity": [10.0, 15.0, 20.0, 25.0],
        "acceleration": [2.0, 2.0, 2.5, 3.0],
        "force": [50.0, 75.0, 100.0, 125.0]
    })
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    files = {"file": ("kinematics_velocity_motion.csv", csv_bytes, "text/csv")}
    data = {
        "title": "Quantum Spin and Velocity Mechanics Lab",
        "description": "High accuracy experimental physics velocity and acceleration measurements",
        "ai_training_allowed": "true",
        "consent_agreed": "true"
    }

    upload_res = client.post("/api/v1/uploads", headers=headers, data=data, files=files)
    assert upload_res.status_code == 201
    upload = upload_res.json()

    # Verify AI Classification
    assert upload["category_confidence"] is not None
    assert upload["category_confidence"] >= 0.75
    assert upload["status"] in ["uploaded", "analyzed"]

    # Verify AI Analysis Endpoint
    analysis_res = client.get(f"/api/v1/uploads/{upload['id']}/analysis", headers=headers)
    assert analysis_res.status_code == 200
    analysis = analysis_res.json()

    assert analysis["total_score"] > 0
    assert analysis["quality"] > 0
    assert analysis["authenticity"] > 0
    assert analysis["uniqueness"] > 0
    assert analysis["metadata_accuracy"] > 0
    assert len(analysis["explanation"]) > 0
    assert len(analysis["tips"]) > 0
    assert analysis["classification_output"]["primary_category"] == "physics"

def test_price_adjustment_within_ai_range(client: TestClient):
    headers = get_auth_headers(client, "seller@example.com", "contributor")
    image_bytes = create_dummy_image()

    files = {"file": ("solar_telescope_image.png", image_bytes, "image/png")}
    data = {
        "title": "Solar Telescope Flare Observations",
        "description": "High resolution astronomy dataset of solar flares and sunspots",
        "ai_training_allowed": "true",
        "consent_agreed": "true"
    }

    upload_res = client.post("/api/v1/uploads", headers=headers, data=data, files=files)
    upload = upload_res.json()
    upload_id = upload["id"]
    min_price = upload["ai_min_price"]
    max_price = upload["ai_max_price"]

    # 1. Valid price inside range -> Should succeed
    valid_price = (min_price + max_price) // 2
    patch_res = client.patch(
        f"/api/v1/uploads/{upload_id}/price",
        headers=headers,
        json={"price_paise": valid_price}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["price_paise"] == valid_price

    # 2. Invalid price below min_price -> Should fail (400)
    low_res = client.patch(
        f"/api/v1/uploads/{upload_id}/price",
        headers=headers,
        json={"price_paise": min_price - 10000}
    )
    assert low_res.status_code == 400
    assert "range" in low_res.json()["detail"].lower()

    # 3. Invalid price above max_price -> Should fail (400)
    high_res = client.patch(
        f"/api/v1/uploads/{upload_id}/price",
        headers=headers,
        json={"price_paise": max_price + 10000}
    )
    assert high_res.status_code == 400
    assert "range" in high_res.json()["detail"].lower()

def test_category_change_request_flow(client: TestClient):
    headers = get_auth_headers(client, "chef@example.com", "contributor")
    image_bytes = create_dummy_image()

    files = {"file": ("food_dataset.png", image_bytes, "image/png")}
    data = {
        "title": "Gourmet Cuisine Recipe Dataset",
        "description": "Culinary recipes and restaurant nutrition data",
        "ai_training_allowed": "true",
        "consent_agreed": "true"
    }

    upload_res = client.post("/api/v1/uploads", headers=headers, data=data, files=files)
    upload = upload_res.json()
    upload_id = upload["id"]

    # Fetch Categories to get target category id (e.g. Business)
    cat_res = client.get("/api/v1/categories")
    categories = cat_res.json()
    business_cat = next(c for c in categories if c["slug"] == "business")

    # Request category change to Business
    patch_cat_res = client.patch(
        f"/api/v1/uploads/{upload_id}/category",
        headers=headers,
        json={"category_id": business_cat["id"]}
    )
    assert patch_cat_res.status_code == 200
    updated_upload = patch_cat_res.json()
    assert updated_upload["category_id"] == business_cat["id"]
    assert updated_upload["category_source"] == "contributor"
