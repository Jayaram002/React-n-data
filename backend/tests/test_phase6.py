import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.ledger import (
    Wallet, LedgerEntry, PayoutRequest, 
    AccountType, EntryDirection, EntryKind, PayoutStatus
)

def get_auth_headers(client: TestClient, email: str, role: str = "contributor", display_name: str = "Data Creator"):
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "role": role,
        "display_name": display_name
    })
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def create_published_listing(client: TestClient, contributor_email: str = "seller_p6@data.com"):
    contrib_headers = get_auth_headers(client, contributor_email, "contributor", "Pro Seller")
    
    df = pd.DataFrame({
        "customer_id": [101, 102, 103],
        "leads_converted": [12, 88, 45],
        "sales_revenue": [25000, 120000, 45000]
    })
    files = {"file": ("sales_funnel_p6.csv", df.to_csv(index=False).encode("utf-8"), "text/csv")}
    data = {
        "title": "B2B Enterprise Sales Conversion Funnel",
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

    # Retrieve listing ID
    browse_res = client.get("/api/v1/listings/browse")
    assert browse_res.status_code == 200
    listing = next(item for item in browse_res.json()["items"] if item["upload_id"] == upload_id)
    listing_id = listing["id"]
    
    return listing_id, upload_id, price_paise, contrib_headers

def test_contributor_earnings_summary_and_wallet_tracking(client: TestClient):
    listing_id, upload_id, price_paise, contrib_headers = create_published_listing(client, "seller_summary@data.com")
    buyer_headers = get_auth_headers(client, "buyer_summary@fund.com", "agency", "Buyer One")

    # Initial earnings check (should be zero)
    e_init = client.get("/api/v1/earnings/me", headers=contrib_headers).json()
    assert e_init["wallet"]["available_balance_paise"] == 0
    assert e_init["lifetime_earnings_paise"] == 0
    assert e_init["sales_count"] == 0

    # 1. Buyer purchases listing
    order = client.post("/api/v1/orders", headers=buyer_headers, json={"listing_id": listing_id}).json()
    client.post(f"/api/v1/mock/orders/{order['id']}/simulate", json={"result": "paid"})

    # 2. Check earnings again
    e_after = client.get("/api/v1/earnings/me", headers=contrib_headers).json()
    expected_share = (price_paise * 80) // 100

    assert e_after["wallet"]["available_balance_paise"] == expected_share
    assert e_after["lifetime_earnings_paise"] == expected_share
    assert e_after["sales_count"] == 1
    assert len(e_after["recent_sales"]) == 1
    assert e_after["recent_sales"][0]["contributor_share_paise"] == expected_share
    assert e_after["recent_sales"][0]["dataset_title"] == "B2B Enterprise Sales Conversion Funnel"

def test_dispute_window_release_pending_mechanism(client: TestClient, db_session: Session):
    listing_id, upload_id, price_paise, contrib_headers = create_published_listing(client, "seller_pending@data.com")

    # Manually place funds in pending balance to simulate active dispute window
    from app.models.upload import Upload
    upload = db_session.query(Upload).filter(Upload.id == upload_id).first()
    wallet = db_session.query(Wallet).filter(Wallet.user_id == upload.contributor_id).first()
    wallet.pending_balance_paise = 25000 # 250 USD
    wallet.available_balance_paise = 5000 # 50 USD
    db_session.commit()

    # Trigger release pending endpoint
    rel_res = client.post("/api/v1/earnings/release-pending", headers=contrib_headers)
    assert rel_res.status_code == 200
    rel_data = rel_res.json()
    assert rel_data["status"] == "success"
    assert rel_data["released_amount_paise"] == 25000

    # Verify wallet has 30,000 available and 0 pending
    wallet_res = client.get("/api/v1/earnings/wallet", headers=contrib_headers).json()
    assert wallet_res["pending_balance_paise"] == 0
    assert wallet_res["available_balance_paise"] == 30000

def test_payout_request_validation(client: TestClient, db_session: Session):
    listing_id, upload_id, price_paise, contrib_headers = create_published_listing(client, "seller_payout_val@data.com")

    # 1. Attempt payout with 0 balance -> 400 Bad Request
    p_fail1 = client.post("/api/v1/payouts/request", headers=contrib_headers, json={
        "amount_paise": 5000,
        "method": "bank_transfer",
        "destination": "A/C: 12345 (IFSC: HDFC0001)"
    })
    assert p_fail1.status_code == 400
    assert "Insufficient available balance" in p_fail1.json()["detail"]

    # 2. Attempt payout below minimum (e.g. 500 paise = $5) -> 400 Bad Request
    p_fail2 = client.post("/api/v1/payouts/request", headers=contrib_headers, json={
        "amount_paise": 500,
        "method": "bank_transfer",
        "destination": "A/C: 12345 (IFSC: HDFC0001)"
    })
    assert p_fail2.status_code == 400
    assert "Minimum payout amount" in p_fail2.json()["detail"]

    # 3. Credit wallet and request valid payout
    from app.models.upload import Upload
    upload = db_session.query(Upload).filter(Upload.id == upload_id).first()
    wallet = db_session.query(Wallet).filter(Wallet.user_id == upload.contributor_id).first()
    wallet.available_balance_paise = 20000 # 200 USD
    db_session.commit()

    p_success = client.post("/api/v1/payouts/request", headers=contrib_headers, json={
        "amount_paise": 15000,
        "method": "bank_transfer",
        "destination": "A/C: 501004829102 (IFSC: HDFC0001234)"
    })
    assert p_success.status_code == 201
    payout = p_success.json()
    assert payout["amount_paise"] == 15000
    assert payout["status"] == "requested"

    # Verify wallet decreased by 15000 (remaining: 5000)
    w_check = client.get("/api/v1/earnings/wallet", headers=contrib_headers).json()
    assert w_check["available_balance_paise"] == 5000

    # Verify Ledger Debit entry
    ledger_debit = (
        db_session.query(LedgerEntry)
        .filter(
            LedgerEntry.account_id == upload.contributor_id,
            LedgerEntry.kind == EntryKind.PAYOUT,
            LedgerEntry.direction == EntryDirection.DEBIT
        )
        .first()
    )
    assert ledger_debit is not None
    assert ledger_debit.amount_paise == 15000

def test_payout_processing_complete_and_reject_refund(client: TestClient, db_session: Session):
    listing_id, upload_id, _, contrib_headers = create_published_listing(client, "seller_proc@data.com")

    from app.models.upload import Upload
    upload = db_session.query(Upload).filter(Upload.id == upload_id).first()
    wallet = db_session.query(Wallet).filter(Wallet.user_id == upload.contributor_id).first()
    wallet.available_balance_paise = 50000
    db_session.commit()

    # 1. Request Payout 1 (20,000 paise)
    p1 = client.post("/api/v1/payouts/request", headers=contrib_headers, json={
        "amount_paise": 20000,
        "method": "upi",
        "destination": "contributor@okhdfcbank"
    }).json()

    # Complete Payout 1
    comp_res = client.post(f"/api/v1/payouts/{p1['id']}/process", headers=contrib_headers, json={
        "action": "complete"
    })
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "completed"

    # 2. Request Payout 2 (15,000 paise)
    p2 = client.post("/api/v1/payouts/request", headers=contrib_headers, json={
        "amount_paise": 15000,
        "method": "bank_transfer",
        "destination": "A/C: invalid_acct"
    }).json()

    # Wallet currently has 50000 - 20000 - 15000 = 15000
    w_mid = client.get("/api/v1/earnings/wallet", headers=contrib_headers).json()
    assert w_mid["available_balance_paise"] == 15000

    # Reject Payout 2 (Simulate bank rejection)
    rej_res = client.post(f"/api/v1/payouts/{p2['id']}/process", headers=contrib_headers, json={
        "action": "reject",
        "reason": "Invalid account number"
    })
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "rejected"

    # Wallet must be refunded 15000 -> 30000
    w_final = client.get("/api/v1/earnings/wallet", headers=contrib_headers).json()
    assert w_final["available_balance_paise"] == 30000

    # Verify Refund Ledger Entry
    refund_entry = (
        db_session.query(LedgerEntry)
        .filter(
            LedgerEntry.account_id == upload.contributor_id,
            LedgerEntry.kind == EntryKind.REFUND,
            LedgerEntry.direction == EntryDirection.CREDIT
        )
        .first()
    )
    assert refund_entry is not None
    assert refund_entry.amount_paise == 15000
