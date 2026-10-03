import io
import pytest
from PIL import Image
import pandas as pd
from fastapi.testclient import TestClient

def get_auth_headers(client: TestClient, email: str, role: str = "contributor", display_name: str = "Contributor"):
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "role": role,
        "display_name": display_name
    })
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def create_dummy_image(color=(40, 90, 180), size=(100, 100)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_publish_and_unpublish_lifecycle(client: TestClient):
    headers = get_auth_headers(client, "alice@science.org", "contributor", "Alice Physicist")

    # 1. Upload Physics dataset
    df = pd.DataFrame({"particle_spin": [0.5, 1.0, 1.5], "energy_ev": [120, 240, 360]})
    files = {"file": ("quantum_particles.csv", df.to_csv(index=False).encode("utf-8"), "text/csv")}
    data = {
        "title": "Quantum Particles Energy Levels",
        "description": "Experimental quantum spin physics measurements",
        "ai_training_allowed": "true",
        "consent_agreed": "true"
    }

    upload_res = client.post("/api/v1/uploads", headers=headers, data=data, files=files)
    assert upload_res.status_code == 201
    upload = upload_res.json()
    upload_id = upload["id"]

    # 2. Publish upload
    pub_res = client.post(f"/api/v1/uploads/{upload_id}/publish", headers=headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "published"

    # 3. Check Marketplace browse
    browse_res = client.get("/api/v1/listings/browse")
    assert browse_res.status_code == 200
    items = browse_res.json()["items"]
    assert len(items) >= 1
    target = next((item for item in items if item["upload_id"] == upload_id), None)
    assert target is not None
    assert target["title"] == "Quantum Particles Energy Levels"

    # 4. Unpublish upload
    unpub_res = client.post(f"/api/v1/uploads/{upload_id}/unpublish", headers=headers)
    assert unpub_res.status_code == 200
    assert unpub_res.json()["status"] == "unpublished"

    # 5. Check no longer active in browse
    browse_res2 = client.get("/api/v1/listings/browse")
    items2 = browse_res2.json()["items"]
    target2 = next((item for item in items2 if item["upload_id"] == upload_id), None)
    assert target2 is None

def test_two_contributors_same_domain_aggregation(client: TestClient):
    headers1 = get_auth_headers(client, "user1_phys@lab.org", "contributor", "Lab 1")
    headers2 = get_auth_headers(client, "user2_phys@lab.org", "contributor", "Lab 2")

    # Contributor 1 uploads Physics CSV
    df1 = pd.DataFrame({"velocity": [10.0, 20.0], "time": [1.0, 2.0]})
    f1 = {"file": ("mechanics_motion.csv", df1.to_csv(index=False).encode("utf-8"), "text/csv")}
    d1 = {"title": "Classical Mechanics Velocity Track", "description": "Kinematics mechanics motion experiment", "ai_training_allowed": "true", "consent_agreed": "true"}
    u1 = client.post("/api/v1/uploads", headers=headers1, data=d1, files=f1).json()
    client.post(f"/api/v1/uploads/{u1['id']}/publish", headers=headers1)

    # Contributor 2 uploads Physics Image
    img_bytes = create_dummy_image(color=(200, 100, 50))
    f2 = {"file": ("solar_cosmic_telescope.png", img_bytes, "image/png")}
    d2 = {"title": "Astrophysics Solar Flare Spectrum", "description": "Cosmic galaxy solar telescope observation", "ai_training_allowed": "true", "consent_agreed": "true"}
    u2 = client.post("/api/v1/uploads", headers=headers2, data=d2, files=f2).json()
    client.post(f"/api/v1/uploads/{u2['id']}/publish", headers=headers2)

    # Verify both appear under Physics domain in Category API
    cat_res = client.get("/api/v1/categories/physics/listings")
    assert cat_res.status_code == 200
    items = cat_res.json()["items"]
    assert len(items) == 2
    titles = [i["title"] for i in items]
    assert "Classical Mechanics Velocity Track" in titles
    assert "Astrophysics Solar Flare Spectrum" in titles

    # Verify Category Tree reports count = 2 for Physics
    tree_res = client.get("/api/v1/categories")
    categories = tree_res.json()
    physics_cat = next(c for c in categories if c["slug"] == "physics")
    assert physics_cat["published_count"] == 2

def test_marketplace_filters_and_preview(client: TestClient):
    headers = get_auth_headers(client, "biz_analyst@corp.com", "contributor", "Biz Analyst")

    # Upload & publish Business CSV
    df = pd.DataFrame({"revenue": [1000, 2000, 3000], "leads": [50, 75, 100]})
    f = {"file": ("sales_pipeline.csv", df.to_csv(index=False).encode("utf-8"), "text/csv")}
    d = {"title": "Enterprise Sales Pipeline Q3", "description": "B2B marketing and sales conversion funnels", "ai_training_allowed": "true", "consent_agreed": "true"}
    u = client.post("/api/v1/uploads", headers=headers, data=d, files=f).json()
    client.post(f"/api/v1/uploads/{u['id']}/publish", headers=headers)

    # 1. Filter by data_type = tabular
    res_tab = client.get("/api/v1/listings/browse?data_type=tabular")
    assert res_tab.status_code == 200
    assert len(res_tab.json()["items"]) >= 1

    # 2. Filter by search query 'sales'
    res_q = client.get("/api/v1/listings/browse?q=sales")
    assert res_q.status_code == 200
    assert len(res_q.json()["items"]) >= 1

    # 3. Test Listing Detail endpoint
    listing_id = res_q.json()["items"][0]["id"]
    detail_res = client.get(f"/api/v1/listings/{listing_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["title"] == "Enterprise Sales Pipeline Q3"
    assert detail["ai_analysis"] is not None
    assert detail["ai_analysis"]["total_score"] > 0

    # 4. Test Listing Safe Preview endpoint
    preview_res = client.get(f"/api/v1/listings/{listing_id}/preview")
    assert preview_res.status_code == 200
    preview_json = preview_res.json()
    assert "sample_rows" in preview_json
