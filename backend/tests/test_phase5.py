import io
import pytest
from PIL import Image
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.ledger import LedgerEntry, Wallet, EntryDirection
from app.models.order import Order, OrderStatus, License
from app.models.audit import DownloadLog

def get_auth_headers(client: TestClient, email: str, role: str = "agency", display_name: str = "Test User"):
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "role": role,
        "display_name": display_name
    })
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def create_published_listing(client: TestClient, contributor_email: str = "contributor_p5@test.com"):
    contrib_headers = get_auth_headers(client, contributor_email, "contributor", "Data Pro")
    
    df = pd.DataFrame({
        "customer_id": [101, 102, 103],
        "leads_converted": [12, 88, 45],
        "sales_revenue": [25000, 120000, 45000]
    })
    files = {"file": ("enterprise_sales_funnel.csv", df.to_csv(index=False).encode("utf-8"), "text/csv")}
    data = {
        "title": "B2B Enterprise Sales and Revenue Leads",
        "description": "Enterprise sales deals, revenue metrics, and CRM funnel leads telemetry data",
        "ai_training_allowed": "true",
        "consent_agreed": "true"
    }
    upload_res = client.post("/api/v1/uploads", headers=contrib_headers, data=data, files=files)
    assert upload_res.status_code == 201
    upload = upload_res.json()
    upload_id = upload["id"]
    price_paise = upload["price_paise"]

    # Publish
    pub_res = client.post(f"/api/v1/uploads/{upload_id}/publish", headers=contrib_headers)
    assert pub_res.status_code == 200

    # Retrieve published listing id
    browse_res = client.get("/api/v1/listings/browse")
    assert browse_res.status_code == 200
    listing = next(item for item in browse_res.json()["items"] if item["upload_id"] == upload_id)
    listing_id = listing["id"]
    
    return listing_id, upload_id, price_paise, contrib_headers


def test_order_creation_and_self_purchase_block(client: TestClient):
    listing_id, upload_id, price_paise, contrib_headers = create_published_listing(client, "author@corp.com")
    buyer_headers = get_auth_headers(client, "buyer@agency.com", "agency", "Acme Agency")

    # 1. Contributor attempting to buy their own listing should fail (400)
    self_buy_res = client.post("/api/v1/orders", headers=contrib_headers, json={"listing_id": listing_id})
    assert self_buy_res.status_code == 400
    assert "Cannot purchase your own listing" in self_buy_res.json()["detail"]

    # 2. Agency buyer creates order -> 201 Created
    order_res = client.post("/api/v1/orders", headers=buyer_headers, json={"listing_id": listing_id})
    assert order_res.status_code == 201
    order = order_res.json()
    assert order["status"] == "awaiting_payment"
    assert order["amount_paise"] == price_paise
    assert order["listing_id"] == listing_id

    # 3. Check Order detail endpoint
    get_res = client.get(f"/api/v1/orders/{order['id']}", headers=buyer_headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == order["id"]

def test_mock_payment_simulation_paid_80_20_split(client: TestClient, db_session: Session):
    listing_id, upload_id, price_paise, _ = create_published_listing(client, "seller1@data.com")
    buyer_headers = get_auth_headers(client, "buyer1@fund.com", "agency", "Venture Fund")

    # Create order
    order_res = client.post("/api/v1/orders", headers=buyer_headers, json={"listing_id": listing_id})
    order_id = order_res.json()["id"]

    # Get checkout details
    checkout_res = client.get(f"/api/v1/mock/orders/{order_id}/checkout")
    assert checkout_res.status_code == 200
    assert checkout_res.json()["amount_paise"] == price_paise

    # Simulate successful payment
    sim_res = client.post(f"/api/v1/mock/orders/{order_id}/simulate", json={"result": "paid"})
    assert sim_res.status_code == 200
    order_data = sim_res.json()
    assert order_data["status"] == "paid"
    assert order_data["license"] is not None
    assert order_data["license"]["type"] == "non_exclusive_commercial"

    # Verify Ledger Entries in DB
    ledger_entries = db_session.query(LedgerEntry).filter(LedgerEntry.order_id == order_id).all()
    assert len(ledger_entries) == 3

    buyer_entry = next(e for e in ledger_entries if e.account_type.value == "buyer")
    contrib_entry = next(e for e in ledger_entries if e.account_type.value == "contributor")
    platform_entry = next(e for e in ledger_entries if e.account_type.value == "platform")

    expected_contrib = (price_paise * 80) // 100
    expected_platform = price_paise - expected_contrib

    assert buyer_entry.direction == EntryDirection.DEBIT
    assert buyer_entry.amount_paise == price_paise

    assert contrib_entry.direction == EntryDirection.CREDIT
    assert contrib_entry.amount_paise == expected_contrib  # 80%

    assert platform_entry.direction == EntryDirection.CREDIT
    assert platform_entry.amount_paise == expected_platform  # 20%

    # Invariance check: Debits == Credits
    total_debit = sum(e.amount_paise for e in ledger_entries if e.direction == EntryDirection.DEBIT)
    total_credit = sum(e.amount_paise for e in ledger_entries if e.direction == EntryDirection.CREDIT)
    assert total_debit == total_credit == price_paise

    # Verify Contributor Wallet
    from app.models.upload import Upload
    upload = db_session.query(Upload).filter(Upload.id == upload_id).first()
    wallet = db_session.query(Wallet).filter(Wallet.user_id == upload.contributor_id).first()
    assert wallet is not None
    assert (wallet.available_balance_paise + wallet.pending_balance_paise) == expected_contrib


def test_payment_idempotency(client: TestClient, db_session: Session):
    listing_id, *_ = create_published_listing(client, "seller_idem@data.com")
    buyer_headers = get_auth_headers(client, "buyer_idem@fund.com", "agency", "Idem Buyer")

    order_res = client.post("/api/v1/orders", headers=buyer_headers, json={"listing_id": listing_id})
    order_id = order_res.json()["id"]

    # First 'paid' event
    client.post(f"/api/v1/mock/orders/{order_id}/simulate", json={"result": "paid"})
    entries_count_1 = db_session.query(LedgerEntry).filter(LedgerEntry.order_id == order_id).count()
    licenses_count_1 = db_session.query(License).filter(License.order_id == order_id).count()
    assert entries_count_1 == 3
    assert licenses_count_1 == 1

    # Second duplicate 'paid' event
    sim2_res = client.post(f"/api/v1/mock/orders/{order_id}/simulate", json={"result": "paid"})
    assert sim2_res.status_code == 200
    assert sim2_res.json()["status"] == "paid"

    entries_count_2 = db_session.query(LedgerEntry).filter(LedgerEntry.order_id == order_id).count()
    licenses_count_2 = db_session.query(License).filter(License.order_id == order_id).count()
    assert entries_count_2 == 3  # No extra ledger records
    assert licenses_count_2 == 1  # No extra license records

def test_mock_payment_failure_and_cancellation(client: TestClient):
    listing_id, *_ = create_published_listing(client, "seller_fail@data.com")
    buyer_headers = get_auth_headers(client, "buyer_fail@fund.com", "agency", "Fail Buyer")

    # 1. Order 1 -> Simulate Failed
    o1 = client.post("/api/v1/orders", headers=buyer_headers, json={"listing_id": listing_id}).json()
    f_res = client.post(f"/api/v1/mock/orders/{o1['id']}/simulate", json={"result": "failed"})
    assert f_res.status_code == 200
    assert f_res.json()["status"] == "failed"

    # 2. Order 2 -> Simulate Cancelled
    o2 = client.post("/api/v1/orders", headers=buyer_headers, json={"listing_id": listing_id}).json()
    c_res = client.post(f"/api/v1/mock/orders/{o2['id']}/simulate", json={"result": "cancelled"})
    assert c_res.status_code == 200
    assert c_res.json()["status"] == "cancelled"

def test_dataset_download_and_audit(client: TestClient, db_session: Session):
    listing_id, upload_id, price_paise, _ = create_published_listing(client, "seller_dl@data.com")
    buyer_headers = get_auth_headers(client, "buyer_dl@agency.com", "agency", "Download Buyer")
    other_headers = get_auth_headers(client, "eavesdropper@intruder.com", "agency", "Eavesdropper")


    order = client.post("/api/v1/orders", headers=buyer_headers, json={"listing_id": listing_id}).json()
    order_id = order["id"]

    # 1. Attempt download before paying -> 400 Bad Request
    unpaid_dl = client.get(f"/api/v1/orders/{order_id}/download", headers=buyer_headers)
    assert unpaid_dl.status_code == 400

    # 2. Simulate Payment Paid
    client.post(f"/api/v1/mock/orders/{order_id}/simulate", json={"result": "paid"})

    # 3. Unauthorized other user attempts download -> 403 Forbidden
    unauth_dl = client.get(f"/api/v1/orders/{order_id}/download", headers=other_headers)
    assert unauth_dl.status_code == 403

    # 4. Authorized buyer downloads -> 200 OK with CSV bytes
    auth_dl = client.get(f"/api/v1/orders/{order_id}/download", headers=buyer_headers)
    assert auth_dl.status_code == 200
    assert "text/csv" in auth_dl.headers.get("content-type", "")
    assert "attachment" in auth_dl.headers.get("content-disposition", "")
    content = auth_dl.text
    assert "customer_id" in content
    assert "leads_converted" in content

    # 5. Verify DownloadLog created
    log = db_session.query(DownloadLog).order_by(DownloadLog.id.desc()).first()
    assert log is not None

