import pytest
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.upload import Upload, UploadStatus, CategorySource
from app.models.audit import Flag, FlagStatus, AuditLog

def get_auth_headers(client: TestClient, email: str, role: str = "admin", display_name: str = "Super Admin"):
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "role": role,
        "display_name": display_name
    })
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_admin_rbac_protection(client: TestClient):
    contrib_headers = get_auth_headers(client, "norm_user@corp.com", "contributor", "Normal Contributor")
    agency_headers = get_auth_headers(client, "norm_agency@agency.com", "agency", "Normal Agency")

    # Contributor & Agency should receive 403 Forbidden
    assert client.get("/api/v1/admin/moderation/queue", headers=contrib_headers).status_code == 403
    assert client.get("/api/v1/admin/analytics", headers=contrib_headers).status_code == 403
    assert client.post("/api/v1/admin/taxonomy/categories", headers=contrib_headers, json={"name": "Bio", "slug": "bio"}).status_code == 403

    assert client.get("/api/v1/admin/moderation/queue", headers=agency_headers).status_code == 403
    assert client.get("/api/v1/admin/analytics", headers=agency_headers).status_code == 403

def test_admin_moderation_queue_and_actions(client: TestClient, db_session: Session):
    admin_headers = get_auth_headers(client, "admin_mod@reactndata.com", "admin", "Admin Mod")
    contrib_headers = get_auth_headers(client, "contrib_mod@data.com", "contributor", "Flagged Contributor")

    # 1. Contributor uploads a dataset
    df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30]})
    files = {"file": ("ambiguous_data.csv", df.to_csv(index=False).encode("utf-8"), "text/csv")}
    data = {
        "title": "Ambiguous Raw Sensor Data",
        "description": "Uncertain measurements without clear domain classification",
        "ai_training_allowed": "true",
        "consent_agreed": "true"
    }
    upload = client.post("/api/v1/uploads", headers=contrib_headers, data=data, files=files).json()
    upload_id = upload["id"]

    # Manually flag upload to simulate security/quality review
    flag = Flag(upload_id=upload_id, reason="Ambiguous column schema requiring manual admin verification", source="system", status=FlagStatus.OPEN)
    db_session.add(flag)
    db_session.commit()

    # 2. Check Moderation Queue
    queue_res = client.get("/api/v1/admin/moderation/queue", headers=admin_headers)
    assert queue_res.status_code == 200
    queue = queue_res.json()
    assert len(queue) >= 1
    mod_item = next(item for item in queue if item["id"] == upload_id)
    assert mod_item["flags_count"] >= 1
    assert len(mod_item["open_flags"]) >= 1

    # 3. Admin assigns domain category and approves
    physics_cat = db_session.query(Category).filter(Category.slug == "physics").first()
    action_res = client.post(
        f"/api/v1/admin/moderation/uploads/{upload_id}/action",
        headers=admin_headers,
        json={
            "action": "approve",
            "category_id": physics_cat.id,
            "reason": "Verified as physics laboratory sensor data"
        }
    )
    assert action_res.status_code == 200
    assert action_res.json()["upload_status"] == "analyzed"

    # Verify upload was updated
    u_check = db_session.query(Upload).filter(Upload.id == upload_id).first()
    assert u_check.category_id == physics_cat.id
    assert u_check.category_source == CategorySource.ADMIN
    assert u_check.price_paise is not None

def test_admin_flag_resolution(client: TestClient, db_session: Session):
    admin_headers = get_auth_headers(client, "admin_flag@reactndata.com", "admin", "Admin Flag")
    contrib_headers = get_auth_headers(client, "contrib_flag@data.com", "contributor", "Flag Contrib")

    df = pd.DataFrame({"a": [1, 2]})
    files = {"file": ("flag_test.csv", df.to_csv(index=False).encode("utf-8"), "text/csv")}
    u = client.post("/api/v1/uploads", headers=contrib_headers, data={"title": "Data", "description": "Desc", "ai_training_allowed": "true", "consent_agreed": "true"}, files=files).json()

    flag = Flag(upload_id=u["id"], reason="Suspected outlier values", source="user", status=FlagStatus.OPEN)
    db_session.add(flag)
    db_session.commit()

    # Admin resolves flag
    res_flag = client.post(
        f"/api/v1/admin/flags/{flag.id}/resolve",
        headers=admin_headers,
        json={"action": "resolve", "notes": "Outlier verified as valid physical measurement"}
    )
    assert res_flag.status_code == 200
    assert res_flag.json()["flag_status"] == "resolved"

def test_admin_taxonomy_crud(client: TestClient):
    admin_headers = get_auth_headers(client, "admin_tax@reactndata.com", "admin", "Admin Tax")

    # 1. Create top-level domain category
    create_res = client.post(
        "/api/v1/admin/taxonomy/categories",
        headers=admin_headers,
        json={
            "name": "Quantum Genomics",
            "slug": "quantum-genomics",
            "base_price_paise": 650000,
            "active": True
        }
    )
    assert create_res.status_code == 201
    cat_id = create_res.json()["id"]

    # 2. Update category
    patch_res = client.patch(
        f"/api/v1/admin/taxonomy/categories/{cat_id}",
        headers=admin_headers,
        json={"base_price_paise": 750000}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["base_price_paise"] == 750000
    assert patch_res.json()["version"] == 2

    # 3. Create Subcategory
    sub_res = client.post(
        "/api/v1/admin/taxonomy/subcategories",
        headers=admin_headers,
        json={
            "parent_id": cat_id,
            "name": "CRISPR Base Sequencing",
            "slug": "crispr-base-sequencing",
            "base_price_paise": 800000,
            "active": True
        }
    )
    assert sub_res.status_code == 201
    sub_id = sub_res.json()["id"]

    # 4. Verify in Public Categories Tree
    tree_res = client.get("/api/v1/categories")
    assert tree_res.status_code == 200
    tree = tree_res.json()
    new_cat = next(c for c in tree if c["slug"] == "quantum-genomics")
    assert new_cat["base_price_paise"] == 750000
    assert len(new_cat["subcategories"]) == 1
    assert new_cat["subcategories"][0]["slug"] == "crispr-base-sequencing"

def test_admin_platform_analytics_and_audit_logs(client: TestClient):
    admin_headers = get_auth_headers(client, "admin_analytics@reactndata.com", "admin", "Admin Analytics")
    contrib_headers = get_auth_headers(client, "seller_analytics@data.com", "contributor", "Pro Seller")
    buyer_headers = get_auth_headers(client, "buyer_analytics@agency.com", "agency", "Acme Fund")

    # Upload & Publish
    df = pd.DataFrame({"leads": [10, 20], "sales": [1000, 2000], "revenue": [5000, 10000]})
    files = {"file": ("biz_data.csv", df.to_csv(index=False).encode("utf-8"), "text/csv")}
    u = client.post(
        "/api/v1/uploads",
        headers=contrib_headers,
        data={"title": "B2B Sales CRM Revenue", "description": "Enterprise sales deals and leads data", "ai_training_allowed": "true", "consent_agreed": "true"},
        files=files
    ).json()
    client.post(f"/api/v1/uploads/{u['id']}/publish", headers=contrib_headers)

    # Buy listing
    browse = client.get("/api/v1/listings/browse").json()
    listing_id = next(item["id"] for item in browse["items"] if item["upload_id"] == u["id"])
    order = client.post("/api/v1/orders", headers=buyer_headers, json={"listing_id": listing_id}).json()
    client.post(f"/api/v1/mock/orders/{order['id']}/simulate", json={"result": "paid"})

    # 1. Test Platform Analytics
    analytics_res = client.get("/api/v1/admin/analytics", headers=admin_headers)
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert analytics["gmv_paise"] > 0
    assert analytics["platform_revenue_paise"] > 0
    assert analytics["total_active_listings"] >= 1
    assert analytics["total_orders_paid"] >= 1
    assert len(analytics["category_distribution"]) > 0

    # 2. Test Audit Logs
    audit_res = client.get("/api/v1/admin/audit-logs?limit=50", headers=admin_headers)
    assert audit_res.status_code == 200
    audit_page = audit_res.json()
    assert audit_page["total"] >= 1
    actions = [item["action"] for item in audit_page["items"]]
    assert "ORDER_PAID" in actions
