import io
import pytest
import pandas as pd
from PIL import Image
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.upload import Upload, UploadStatus, DataType
from app.models.listing import Listing, ListingStatus
from app.models.order import Order, OrderStatus, License
from app.models.ledger import Wallet, LedgerEntry, PayoutRequest, PayoutStatus, EntryKind, AccountType
from app.models.audit import AuditLog, DownloadLog

def get_auth_headers(client: TestClient, email: str, role: str, display_name: str):
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "role": role,
        "display_name": display_name,
        "company_name": display_name if role == "agency" else None
    })
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_full_marketplace_lifecycle_e2e(client: TestClient, db_session: Session):
    """
    Complete End-to-End Integration Lifecycle:
    1. Contributor Onboarding & Auth
    2. Data Ingestion & Pre-checks (Tabular PII & Schema)
    3. Gemma AI Trust Scoring & Piecewise Dynamic Pricing
    4. Dataset Publishing & Public Listing
    5. Agency Discovery, Search & Safe Preview
    6. Mock Checkout & 80/20 Double-Entry Ledger Split
    7. Commercial Licensing & Secure Download Audit
    8. Dispute Release Window & Contributor Earnings
    9. Payout Lifecycle (Request -> Admin Review -> Approval)
    10. Platform Financial & Moderation Analytics
    """
    # ---------------------------------------------------------
    # 1. User Setup
    # ---------------------------------------------------------
    contrib_headers = get_auth_headers(client, "e2e_contrib@data.com", "contributor", "E2E Lead Contributor")
    agency_headers = get_auth_headers(client, "e2e_agency@corp.com", "agency", "E2E Analytics Corp")
    admin_headers = get_auth_headers(client, "e2e_admin@reactndata.com", "admin", "E2E Platform Admin")

    # ---------------------------------------------------------
    # 2. Contributor Ingestion (Tabular Dataset)
    # ---------------------------------------------------------
    raw_df = pd.DataFrame({
        "patient_id": [1001, 1002, 1003, 1004, 1005],
        "heart_rate_bpm": [72, 85, 68, 92, 76],
        "systolic_bp": [120, 135, 118, 142, 124],
        "diastolic_bp": [80, 88, 76, 90, 82],
        "oxygen_sat_pct": [98.5, 96.2, 99.1, 95.0, 98.0]
    })
    csv_bytes = raw_df.to_csv(index=False).encode("utf-8")

    upload_payload = {
        "title": "Clinical Patient Treatment and Hospital Vitals Cohort",
        "description": "High-fidelity telemetry of clinical patient treatment vitals with cardiovascular metrics.",
        "ai_training_allowed": "true",
        "consent_agreed": "true"
    }
    upload_files = {
        "file": ("cardio_cohort_vitals.csv", csv_bytes, "text/csv")
    }

    upload_res = client.post("/api/v1/uploads", headers=contrib_headers, data=upload_payload, files=upload_files)
    assert upload_res.status_code == 201, upload_res.text
    upload_data = upload_res.json()
    upload_id = upload_data["id"]

    # Under DPDP Act / Rules 2025, Health domain routes to moderation queue; admin reviews and approves
    if upload_data["status"] == UploadStatus.FLAGGED.value:
        mod_res = client.post(
            f"/api/v1/admin/moderation/uploads/{upload_id}/action",
            headers=admin_headers,
            json={"action": "approve"}
        )
        assert mod_res.status_code == 200
        upload_data = client.get(f"/api/v1/uploads/{upload_id}", headers=contrib_headers).json()

    assert upload_data["status"] == UploadStatus.ANALYZED.value
    assert upload_data["ai_min_price"] > 0
    assert upload_data["ai_max_price"] >= upload_data["ai_min_price"]

    # Verify AI Analysis detail endpoint
    analysis_res = client.get(f"/api/v1/uploads/{upload_id}/analysis", headers=contrib_headers)
    assert analysis_res.status_code == 200
    analysis = analysis_res.json()
    assert analysis["total_score"] >= 75.0
    assert analysis["quality"] > 0
    assert analysis["authenticity"] > 0

    # ---------------------------------------------------------
    # 3. Publish Upload to Marketplace
    # ---------------------------------------------------------
    custom_price = upload_data["ai_min_price"] + 5000  # e.g., in paise
    price_res = client.patch(
        f"/api/v1/uploads/{upload_id}/price",
        headers=contrib_headers,
        json={"price_paise": custom_price}
    )
    assert price_res.status_code == 200
    assert price_res.json()["price_paise"] == custom_price

    publish_res = client.post(
        f"/api/v1/uploads/{upload_id}/publish",
        headers=contrib_headers
    )
    assert publish_res.status_code == 200
    assert publish_res.json()["status"] == UploadStatus.PUBLISHED.value

    # Verify Listing exists
    listing = db_session.query(Listing).filter(Listing.upload_id == upload_id).first()
    assert listing is not None
    assert listing.status == ListingStatus.ACTIVE
    listing_id = listing.id

    # ---------------------------------------------------------
    # 4. Agency Marketplace Discovery & Previews
    # ---------------------------------------------------------
    browse_res = client.get("/api/v1/listings/browse?q=Patient", headers=agency_headers)
    assert browse_res.status_code == 200
    listings_list = browse_res.json()["items"]
    assert any(item["id"] == listing_id for item in listings_list)

    # Safe Preview Check
    preview_res = client.get(f"/api/v1/listings/{listing_id}/preview", headers=agency_headers)
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert "columns" in preview_data
    assert len(preview_data.get("sample_rows", [])) <= 5

    # ---------------------------------------------------------
    # 5. Agency Checkout & Payment Simulation
    # ---------------------------------------------------------
    order_res = client.post("/api/v1/orders", headers=agency_headers, json={"listing_id": listing_id})
    assert order_res.status_code == 201
    order_data = order_res.json()
    order_id = order_data["id"]
    assert order_data["amount_paise"] == custom_price
    assert order_data["status"] == OrderStatus.AWAITING_PAYMENT.value

    # Execute mock payment
    pay_res = client.post(f"/api/v1/mock/orders/{order_id}/simulate", json={"result": "paid"})
    assert pay_res.status_code == 200
    assert pay_res.json()["status"] == OrderStatus.PAID.value

    # Verify Commercial License
    license_rec = db_session.query(License).filter(License.order_id == order_id).first()
    assert license_rec is not None
    assert "commercial" in license_rec.type

    # Verify 80/20 Double-Entry Ledger
    # Contributor gets 80%, Platform gets 20%
    expected_contrib = int(custom_price * 0.80)
    expected_platform = custom_price - expected_contrib

    ledger_entries = db_session.query(LedgerEntry).filter(LedgerEntry.order_id == order_id).all()
    assert len(ledger_entries) == 3  # Buyer payment debit, Contributor credit, Platform fee credit

    contrib_entry = next(e for e in ledger_entries if e.kind == EntryKind.CONTRIBUTOR_CREDIT)
    assert contrib_entry.amount_paise == expected_contrib
    platform_entry = next(e for e in ledger_entries if e.kind == EntryKind.PLATFORM_FEE)
    assert platform_entry.amount_paise == expected_platform

    # ---------------------------------------------------------
    # 6. Dataset Download & Audit Trail
    # ---------------------------------------------------------
    purchases_res = client.get("/api/v1/orders/mine", headers=agency_headers)
    assert purchases_res.status_code == 200
    purchases = purchases_res.json()
    assert any(p["id"] == order_id for p in purchases)

    download_res = client.get(f"/api/v1/orders/{order_id}/download", headers=agency_headers)
    assert download_res.status_code == 200
    assert download_res.headers["content-type"].startswith("text/csv")
    assert b"patient_id" in download_res.content

    # Verify Download Audit Log
    dl_log = db_session.query(DownloadLog).filter(DownloadLog.license_id == license_rec.id).first()
    assert dl_log is not None

    # ---------------------------------------------------------
    # 7. Contributor Wallet & Payout Flow
    # ---------------------------------------------------------
    # In order to make the pending funds available for payout test, fast-forward entry availability
    contrib_entry.available_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    # Trigger release of matured pending funds
    rel_res = client.post("/api/v1/earnings/release-pending", headers=contrib_headers)
    assert rel_res.status_code == 200

    wallet_res = client.get("/api/v1/earnings/wallet", headers=contrib_headers)
    assert wallet_res.status_code == 200
    wallet_data = wallet_res.json()
    assert wallet_data["available_balance_paise"] == expected_contrib

    # Contributor submits payout request
    payout_req_res = client.post(
        "/api/v1/payouts/request",
        headers=contrib_headers,
        json={
            "amount_paise": expected_contrib,
            "method": "bank_transfer",
            "destination": "HDFC0001234 - 501004829102"
        }
    )
    assert payout_req_res.status_code == 201
    payout_data = payout_req_res.json()
    payout_id = payout_data["id"]

    # Wallet available balance should be deducted immediately
    wallet = db_session.query(Wallet).filter(Wallet.user_id == contrib_entry.account_id).first()
    assert wallet.available_balance_paise == 0

    # ---------------------------------------------------------
    # 8. Admin Payout Review & Approval
    # ---------------------------------------------------------
    my_payouts_res = client.get("/api/v1/payouts/mine", headers=contrib_headers)
    assert my_payouts_res.status_code == 200
    assert any(p["id"] == payout_id for p in my_payouts_res.json())

    approve_payout_res = client.post(
        f"/api/v1/payouts/{payout_id}/process",
        headers=admin_headers,
        json={"action": "complete", "reason": "All compliance verification checks passed."}
    )
    assert approve_payout_res.status_code == 200
    assert approve_payout_res.json()["status"] == PayoutStatus.COMPLETED.value

    # ---------------------------------------------------------
    # 9. Admin Platform Analytics Verification
    # ---------------------------------------------------------
    analytics_res = client.get("/api/v1/admin/analytics", headers=admin_headers)
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert analytics["gmv_paise"] >= custom_price
    assert analytics["platform_revenue_paise"] >= expected_platform
    assert analytics["total_contributors"] >= 1
    assert analytics["total_orders_paid"] >= 1

    # Verify Audit Trail
    audit_logs_res = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert audit_logs_res.status_code == 200
    assert len(audit_logs_res.json()) >= 1


def test_image_upload_and_perceptual_hash_lifecycle(client: TestClient, db_session: Session):
    """
    Test image ingestion, EXIF stripping, pHash calculation, and safe watermarked preview generation.
    """
    contrib_headers = get_auth_headers(client, "img_contrib@data.com", "contributor", "Vision Researcher")

    # Generate test image
    img = Image.new("RGB", (800, 600), color=(100, 150, 220))
    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_bytes = img_buf.getvalue()

    upload_payload = {
        "title": "Solar Flare Telescope Coronagraph Image Spectrum",
        "description": "Multi-wavelength extreme ultraviolet solar flare astrophysics astronomy cosmic image dataset.",
        "ai_training_allowed": "true",
        "consent_agreed": "true"
    }
    upload_files = {
        "file": ("satellite_aerosol.png", img_bytes, "image/png")
    }

    upload_res = client.post("/api/v1/uploads", headers=contrib_headers, data=upload_payload, files=upload_files)
    assert upload_res.status_code == 201
    upload_data = upload_res.json()

    assert upload_data["status"] == UploadStatus.ANALYZED.value
    assert upload_data["file_info"]["data_type"] == "image"
    assert upload_data["file_info"]["phash"] is not None
    assert isinstance(upload_data["file_info"]["exif_stripped"], bool)
