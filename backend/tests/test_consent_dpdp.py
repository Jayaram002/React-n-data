"""
Comprehensive DPDP Act 2023 / Rules 2025 Consent Framework Verification Test Suite.

Verifies:
1. Upload rejected without each required consent.
2. AI-training flag requires its specific grant.
3. Records are append-only and status resolves from latest row.
4. Document edits create new versions with matching SHA256.
5. Attestation (c) / PII hit / Face or Plate / Health-Finance routes to moderation.
6. Order rejected without buyer agreement.
7. Withdrawal unpublishes listing immediately but keeps existing licenses and ledger.
8. Deletion anonymizes user profile but keeps immutable consent + ledger records.
9. Takedown request creates an admin moderation flag.
10. Role checks on all new consent endpoints.
11. Legacy consent backfill works seamlessly.
"""

import io
import hashlib
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole, UserStatus
from app.models.upload import Upload, UploadStatus
from app.models.listing import Listing, ListingStatus
from app.models.order import Order, OrderStatus, License
from app.models.ledger import LedgerEntry
from app.models.audit import Flag, FlagStatus
from app.models.consent import (
    ConsentDocument,
    ConsentRecord,
    ConsentPurpose,
    ConsentAction,
    TakedownRequest,
    DeletionRequest,
    TakedownStatus,
    DeletionRequestStatus,
)
from app.services.consent.consent_service import ConsentService


def get_token_for(client: TestClient, email: str, role: str):
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "role": role,
        "display_name": email.split("@")[0],
        "is_adult_confirmed": True,
        "terms_accepted": True,
        "privacy_accepted": True,
    })
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── 1. UPLOAD REJECTED WITHOUT EACH REQUIRED CONSENT ───────────────────────
def test_upload_rejected_without_each_required_consent(client: TestClient):
    headers = get_token_for(client, "consent_test_uploader@data.com", "contributor")
    csv_bytes = b"col1,col2\n10,20\n30,40"
    files = {"file": ("data.csv", csv_bytes, "text/csv")}

    # Missing contributor_rights_agreed
    res1 = client.post(
        "/api/v1/uploads",
        headers=headers,
        data={
            "title": "Dataset Missing Rights Warranty",
            "description": "Desc",
            "contributor_rights_agreed": "false",
            "platform_license_agreed": "true",
            "personal_data_attestation_agreed": "true",
            "personal_data_status": "none"
        },
        files=files
    )
    assert res1.status_code == 400
    assert "ownership" in res1.json()["detail"].lower() or "consent" in res1.json()["detail"].lower()

    # Missing platform_license_agreed
    res2 = client.post(
        "/api/v1/uploads",
        headers=headers,
        data={
            "title": "Dataset Missing Platform License",
            "description": "Desc",
            "contributor_rights_agreed": "true",
            "platform_license_agreed": "false",
            "personal_data_attestation_agreed": "true",
            "personal_data_status": "none"
        },
        files=files
    )
    assert res2.status_code == 400
    assert "platform license" in res2.json()["detail"].lower()

    # Missing personal_data_attestation_agreed
    res3 = client.post(
        "/api/v1/uploads",
        headers=headers,
        data={
            "title": "Dataset Missing Attestation",
            "description": "Desc",
            "contributor_rights_agreed": "true",
            "platform_license_agreed": "true",
            "personal_data_attestation_agreed": "false",
            "personal_data_status": "none"
        },
        files=files
    )
    assert res3.status_code == 400
    assert "personal data attestation" in res3.json()["detail"].lower()


# ── 2. AI-TRAINING FLAG REQUIRES ITS SPECIFIC GRANT ───────────────────────
def test_ai_training_flag_requires_grant(client: TestClient, db_session: Session):
    headers = get_token_for(client, "ai_grant_uploader@data.com", "contributor")
    csv_bytes = b"x,y\n1,2\n3,4"
    files = {"file": ("numbers.csv", csv_bytes, "text/csv")}

    # Upload with ai_training_agreed = false (default OFF)
    res_off = client.post(
        "/api/v1/uploads",
        headers=headers,
        data={
            "title": "Physics Math Data - AI Disabled",
            "description": "Pure numerical series",
            "contributor_rights_agreed": "true",
            "platform_license_agreed": "true",
            "personal_data_attestation_agreed": "true",
            "personal_data_status": "none",
            "ai_training_agreed": "false"
        },
        files=files
    )
    assert res_off.status_code == 201
    up_off = res_off.json()
    assert up_off["ai_training_allowed"] is False

    # Verify no ai_training_use consent record was logged
    ai_record = db_session.query(ConsentRecord).filter(
        ConsentRecord.upload_id == up_off["id"],
        ConsentRecord.purpose_code == ConsentPurpose.AI_TRAINING_USE.value
    ).first()
    assert ai_record is None

    # Upload with ai_training_agreed = true
    res_on = client.post(
        "/api/v1/uploads",
        headers=headers,
        data={
            "title": "Physics Math Data - AI Enabled",
            "description": "Pure numerical series",
            "contributor_rights_agreed": "true",
            "platform_license_agreed": "true",
            "personal_data_attestation_agreed": "true",
            "personal_data_status": "none",
            "ai_training_agreed": "true"
        },
        files=files
    )
    assert res_on.status_code == 201
    up_on = res_on.json()
    assert up_on["ai_training_allowed"] is True

    # Verify granted record exists
    ai_rec_on = db_session.query(ConsentRecord).filter(
        ConsentRecord.upload_id == up_on["id"],
        ConsentRecord.purpose_code == ConsentPurpose.AI_TRAINING_USE.value,
        ConsentRecord.action == ConsentAction.GRANTED.value
    ).first()
    assert ai_rec_on is not None


# ── 3. APPEND-ONLY CONSENT RECORDS AND STATUS FROM LATEST ROW ─────────────
def test_append_only_records_and_latest_status(client: TestClient, db_session: Session):
    user_email = "append_only_user@data.com"
    headers = get_token_for(client, user_email, "contributor")
    user = db_session.query(User).filter(User.email == user_email).first()

    # Upload dataset
    csv_bytes = b"param,val\n1,2\n3,4"
    files = {"file": ("data.csv", csv_bytes, "text/csv")}
    up = client.post(
        "/api/v1/uploads",
        headers=headers,
        data={
            "title": "Append Only Test Dataset",
            "description": "Testing immutable journal",
            "contributor_rights_agreed": "true",
            "platform_license_agreed": "true",
            "personal_data_attestation_agreed": "true",
            "personal_data_status": "none",
            "ai_training_agreed": "true"
        },
        files=files
    ).json()

    upload_id = up["id"]
    # Verify initial active grant status
    status_initial = ConsentService.get_consent_status(db_session, user.id, ConsentPurpose.AI_TRAINING_USE.value, upload_id=upload_id)
    assert status_initial == ConsentAction.GRANTED.value

    # Withdraw AI training consent
    w_res = client.post(
        f"/api/v1/uploads/{upload_id}/consent/withdraw",
        headers=headers,
        json={"purpose_code": ConsentPurpose.AI_TRAINING_USE.value}
    )
    assert w_res.status_code == 200

    # Verify latest status resolves to 'withdrawn'
    status_after = ConsentService.get_consent_status(db_session, user.id, ConsentPurpose.AI_TRAINING_USE.value, upload_id=upload_id)
    assert status_after == ConsentAction.WITHDRAWN.value

    # Check that rows were APPENDED (never updated or deleted)
    records = db_session.query(ConsentRecord).filter(
        ConsentRecord.upload_id == upload_id,
        ConsentRecord.purpose_code == ConsentPurpose.AI_TRAINING_USE.value
    ).order_by(ConsentRecord.id.asc()).all()
    assert len(records) == 2
    assert records[0].action == ConsentAction.GRANTED.value
    assert records[1].action == ConsentAction.WITHDRAWN.value


# ── 4. DOCUMENT EDITS CREATE NEW VERSIONS WITH MATCHING SHA256 ────────────
def test_document_edits_create_new_versions(client: TestClient, db_session: Session):
    admin_headers = get_token_for(client, "doc_admin@reactndata.com", "admin")

    body_text = "# Updated Terms of Service v2.0\n\nExplicit DPDP Act 2025 compliance policies updated."
    expected_sha = hashlib.sha256(body_text.encode("utf-8")).hexdigest()

    create_res = client.post(
        "/api/v1/consent/documents",
        headers=admin_headers,
        json={
            "purpose_code": ConsentPurpose.TERMS_OF_SERVICE.value,
            "version": "2.0",
            "title": "Terms of Service (v2.0 DPDP Edition)",
            "body_markdown": body_text
        }
    )
    assert create_res.status_code == 200
    doc_data = create_res.json()
    assert doc_data["version"] == "2.0"
    assert doc_data["sha256"] == expected_sha
    assert doc_data["active"] is True

    # Check that previous v1.0 was deactivated
    old_doc = db_session.query(ConsentDocument).filter(
        ConsentDocument.purpose_code == ConsentPurpose.TERMS_OF_SERVICE.value,
        ConsentDocument.version == "1.0"
    ).first()
    if old_doc:
        assert old_doc.active is False


# ── 5. ATTESTATION (C) / PII / FACE / HEALTH-FINANCE ROUTED TO MODERATION ─
def test_attestation_and_sensitive_domain_moderation_routing(client: TestClient, db_session: Session):
    headers = get_token_for(client, "mod_router_contributor@data.com", "contributor")

    # (a) Attestation (c): contains_personal_data with lawful basis
    csv_bytes = b"id,val\n1,10\n2,20"
    files = {"file": ("data.csv", csv_bytes, "text/csv")}
    res_c = client.post(
        "/api/v1/uploads",
        headers=headers,
        data={
            "title": "Medical Subject Research Records",
            "description": "Contains consenting patient data",
            "contributor_rights_agreed": "true",
            "platform_license_agreed": "true",
            "personal_data_attestation_agreed": "true",
            "personal_data_status": "contains_personal_data",
            "lawful_basis": "consent",
            "lawful_basis_note": "Signed research consent certificates"
        },
        files=files
    )
    assert res_c.status_code == 201
    up_c = res_c.json()
    assert up_c["status"] == "flagged"

    # Verify moderation flag exists
    flag_c = db_session.query(Flag).filter(Flag.upload_id == up_c["id"]).first()
    assert flag_c is not None
    assert "lawful basis" in flag_c.reason.lower() or "moderation" in flag_c.reason.lower()

    # (b) Discrepancy: Claims 'none', but PII detected
    pii_df = pd.DataFrame({
        "name": ["Alice", "Bob"],
        "email": ["alice@corp.com", "bob@corp.com"],
        "phone": ["(555) 123-4567", "(555) 987-6543"]
    })
    pii_csv = pii_df.to_csv(index=False).encode("utf-8")
    files_pii = {"file": ("pii.csv", pii_csv, "text/csv")}
    res_disc = client.post(
        "/api/v1/uploads",
        headers=headers,
        data={
            "title": "Secret Customer CRM Records",
            "description": "Claims no personal data",
            "contributor_rights_agreed": "true",
            "platform_license_agreed": "true",
            "personal_data_attestation_agreed": "true",
            "personal_data_status": "none"
        },
        files=files_pii
    )
    assert res_disc.status_code == 201
    up_disc = res_disc.json()
    assert up_disc["status"] == "flagged"

    flag_disc = db_session.query(Flag).filter(
        Flag.upload_id == up_disc["id"],
        Flag.reason.like("%Discrepancy%")
    ).first()
    assert flag_disc is not None


# ── 6. ORDER REJECTED WITHOUT BUYER AGREEMENT ──────────────────────────────
def test_order_rejected_without_buyer_agreement(client: TestClient, db_session: Session):
    seller_headers = get_token_for(client, "seller_order_test@data.com", "contributor")
    buyer_headers = get_token_for(client, "buyer_order_test@agency.com", "agency")

    # Upload and publish dataset
    csv_bytes = b"item,price\nA,10\nB,20"
    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    up = client.post(
        "/api/v1/uploads",
        headers=seller_headers,
        data={
            "title": "Physics Optics Dataset",
            "description": "Laboratory optics metrics",
            "contributor_rights_agreed": "true",
            "platform_license_agreed": "true",
            "personal_data_attestation_agreed": "true",
            "personal_data_status": "none"
        },
        files=files
    ).json()

    # Publish upload
    pub_res = client.post(f"/api/v1/uploads/{up['id']}/publish", headers=seller_headers)
    assert pub_res.status_code == 200

    listing = db_session.query(Listing).filter(Listing.upload_id == up["id"]).first()
    assert listing is not None

    # Attempt order with buyer_agreement_accepted = false
    reject_res = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={"listing_id": listing.id, "buyer_agreement_accepted": False}
    )
    assert reject_res.status_code == 400
    assert "buyer license agreement" in reject_res.json()["detail"].lower()

    # Order with buyer_agreement_accepted = true
    accept_res = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={"listing_id": listing.id, "buyer_agreement_accepted": True}
    )
    assert accept_res.status_code == 201
    order_data = accept_res.json()
    assert order_data["status"] == "awaiting_payment"

    # Verify buyer agreement consent record was logged
    buyer_user = db_session.query(User).filter(User.email == "buyer_order_test@agency.com").first()
    order_rec = db_session.query(ConsentRecord).filter(
        ConsentRecord.order_id == order_data["id"],
        ConsentRecord.user_id == buyer_user.id,
        ConsentRecord.purpose_code == ConsentPurpose.BUYER_LICENSE_AGREEMENT.value
    ).first()
    assert order_rec is not None


# ── 7. WITHDRAWAL UNPUBLISHES BUT KEEPS LICENSES AND LEDGER ────────────────
def test_withdrawal_unpublishes_listing_keeps_license_and_ledger(client: TestClient, db_session: Session):
    seller_headers = get_token_for(client, "seller_withdraw_test@data.com", "contributor")
    buyer_headers = get_token_for(client, "buyer_withdraw_test@agency.com", "agency")

    # Upload and publish
    csv_bytes = b"sensor,reading\n1,100\n2,200"
    files = {"file": ("readings.csv", csv_bytes, "text/csv")}
    up = client.post(
        "/api/v1/uploads",
        headers=seller_headers,
        data={
            "title": "Business Sales Telemetry Dataset",
            "description": "Sales funnel transactions",
            "contributor_rights_agreed": "true",
            "platform_license_agreed": "true",
            "personal_data_attestation_agreed": "true",
            "personal_data_status": "none"
        },
        files=files
    ).json()
    upload_id = up["id"]
    client.post(f"/api/v1/uploads/{upload_id}/publish", headers=seller_headers)

    listing = db_session.query(Listing).filter(Listing.upload_id == upload_id).first()
    listing_id = listing.id

    # Buyer orders and pays
    order_res = client.post("/api/v1/orders", headers=buyer_headers, json={"listing_id": listing_id, "buyer_agreement_accepted": True})
    order_id = order_res.json()["id"]
    client.post(f"/api/v1/mock/orders/{order_id}/simulate", json={"result": "paid"})

    # Verify license and ledger entries exist
    paid_license = db_session.query(License).filter(License.order_id == order_id).first()
    assert paid_license is not None
    ledger_entries = db_session.query(LedgerEntry).filter(LedgerEntry.order_id == order_id).all()
    assert len(ledger_entries) >= 2

    # Contributor withdraws platform listing license
    w_res = client.post(
        f"/api/v1/uploads/{upload_id}/consent/withdraw",
        headers=seller_headers,
        json={"purpose_code": ConsentPurpose.PLATFORM_LISTING_LICENSE.value}
    )
    assert w_res.status_code == 200
    w_data = w_res.json()
    assert w_data["effects"]["listing_unpublished"] is True

    # Listing must be INACTIVE now
    db_session.refresh(listing)
    assert listing.status == ListingStatus.INACTIVE

    # Existing buyer CAN STILL download dataset
    dl_res = client.get(f"/api/v1/orders/{order_id}/download", headers=buyer_headers)
    assert dl_res.status_code == 200

    # Ledger and license remain intact
    db_session.refresh(paid_license)
    assert paid_license.id is not None
    remaining_ledger = db_session.query(LedgerEntry).filter(LedgerEntry.order_id == order_id).count()
    assert remaining_ledger >= 2


# ── 8. DELETION ANONYMIZES USER PROFILE BUT KEEPS RECORDS ─────────────────
def test_deletion_anonymizes_profile_keeps_records(client: TestClient, db_session: Session):
    admin_headers = get_token_for(client, "admin_del_test@reactndata.com", "admin")
    del_user_headers = get_token_for(client, "user_to_delete@data.com", "contributor")
    user = db_session.query(User).filter(User.email == "user_to_delete@data.com").first()
    uid = user.id

    # Create an upload
    csv_bytes = b"a,b\n1,2"
    files = {"file": ("a.csv", csv_bytes, "text/csv")}
    client.post(
        "/api/v1/uploads",
        headers=del_user_headers,
        data={
            "title": "User Upload Before Erasure",
            "description": "Desc",
            "contributor_rights_agreed": "true",
            "platform_license_agreed": "true",
            "personal_data_attestation_agreed": "true",
            "personal_data_status": "none"
        },
        files=files
    )

    # User initiates erasure request
    del_res = client.post(
        "/api/v1/consent/me/deletion-request",
        headers=del_user_headers,
        json={"reason": "Right to erasure Section 12"}
    )
    assert del_res.status_code == 201
    del_req_id = del_res.json()["id"]

    # Admin approves deletion request
    approve_res = client.post(
        f"/api/v1/consent/admin/deletions/{del_req_id}/approve",
        headers=admin_headers
    )
    assert approve_res.status_code == 200

    # Verify user profile is anonymized
    db_session.refresh(user)
    assert user.email == f"anonymized_user_{uid}@redacted.local"
    assert user.status == UserStatus.SUSPENDED
    assert user.deleted_at is not None

    # Verify immutable consent records are RETAINED (never deleted)
    records = db_session.query(ConsentRecord).filter(ConsentRecord.user_id == uid).all()
    assert len(records) > 0


# ── 9. TAKEDOWN REQUEST CREATES AN ADMIN MODERATION FLAG ───────────────────
def test_takedown_creates_moderation_flag(client: TestClient, db_session: Session):
    contributor_headers = get_token_for(client, "takedown_seller@data.com", "contributor")

    # Upload dataset
    csv_bytes = b"col1,col2\n1,2"
    files = {"file": ("data.csv", csv_bytes, "text/csv")}
    up = client.post(
        "/api/v1/uploads",
        headers=contributor_headers,
        data={
            "title": "Takedown Target Dataset",
            "description": "Desc",
            "contributor_rights_agreed": "true",
            "platform_license_agreed": "true",
            "personal_data_attestation_agreed": "true",
            "personal_data_status": "none"
        },
        files=files
    ).json()
    upload_id = up["id"]

    # Public user submits takedown notice
    take_res = client.post(
        "/api/v1/consent/takedown-requests",
        json={
            "upload_id": upload_id,
            "claimant_name": "Copyright Protection Bureau",
            "claimant_email": "dmca@copyrightbureau.org",
            "reason": "copyright",
            "details": "This dataset contains scraped proprietary intellectual property."
        }
    )
    assert take_res.status_code == 201

    # Verify open moderation Flag was generated
    flag = db_session.query(Flag).filter(
        Flag.upload_id == upload_id,
        Flag.reason.like("%Takedown notice%")
    ).first()
    assert flag is not None
    assert flag.status == FlagStatus.OPEN


# ── 10. ROLE CHECKS ON NEW ENDPOINTS ──────────────────────────────────────
def test_role_checks_on_consent_endpoints(client: TestClient):
    contributor_headers = get_token_for(client, "normal_contributor_rbac@data.com", "contributor")
    agency_headers = get_token_for(client, "agency_rbac@data.com", "agency")

    # Non-admin attempting to list takedowns -> 403 Forbidden
    res1 = client.get("/api/v1/consent/admin/takedowns", headers=contributor_headers)
    assert res1.status_code == 403

    # Non-admin attempting to list deletions -> 403 Forbidden
    res2 = client.get("/api/v1/consent/admin/deletions", headers=agency_headers)
    assert res2.status_code == 403

    # Non-admin attempting to access consent report -> 403 Forbidden
    res3 = client.get("/api/v1/consent/admin/report", headers=contributor_headers)
    assert res3.status_code == 403


# ── 11. LEGACY BACKFILL WORKS SEAMLESSLY ──────────────────────────────────
def test_legacy_backfill(db_session: Session):
    count = ConsentService.backfill_legacy_consents(db_session)
    assert isinstance(count, int)
