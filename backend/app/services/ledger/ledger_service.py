from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.ledger import (
    Wallet, LedgerEntry, PayoutRequest, 
    AccountType, EntryDirection, EntryKind, PayoutStatus
)
from app.models.order import Order, OrderStatus
from app.models.listing import Listing
from app.models.upload import Upload
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.ledger import (
    ContributorEarningsSummary, WalletOut, SaleItemOut, PayoutRequestOut
)

def get_wallet_or_create(db: Session, user_id: int) -> Wallet:
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        wallet = Wallet(
            user_id=user_id,
            pending_balance_paise=0,
            available_balance_paise=0,
            updated_at=datetime.now(timezone.utc)
        )
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet

def get_contributor_earnings(db: Session, user_id: int) -> ContributorEarningsSummary:
    wallet = get_wallet_or_create(db, user_id)

    # Calculate lifetime earnings (all contributor credits)
    lifetime_earnings = (
        db.query(func.sum(LedgerEntry.amount_paise))
        .filter(
            LedgerEntry.account_type == AccountType.CONTRIBUTOR,
            LedgerEntry.account_id == user_id,
            LedgerEntry.kind == EntryKind.CONTRIBUTOR_CREDIT,
            LedgerEntry.direction == EntryDirection.CREDIT
        )
        .scalar() or 0
    )

    # Calculate lifetime withdrawn (completed payouts)
    lifetime_withdrawn = (
        db.query(func.sum(PayoutRequest.amount_paise))
        .filter(
            PayoutRequest.user_id == user_id,
            PayoutRequest.status == PayoutStatus.COMPLETED
        )
        .scalar() or 0
    )

    # Find sales for this contributor's listings
    paid_orders = (
        db.query(Order)
        .join(Listing, Order.listing_id == Listing.id)
        .join(Upload, Listing.upload_id == Upload.id)
        .filter(
            Upload.contributor_id == user_id,
            Order.status == OrderStatus.PAID
        )
        .order_by(Order.created_at.desc())
        .all()
    )

    sales_items: List[SaleItemOut] = []
    for o in paid_orders:
        upload = o.listing.upload if o.listing else None
        buyer_email = o.buyer.email if o.buyer else "buyer@marketplace"
        share_paise = (o.amount_paise * 80) // 100
        data_type_str = "tabular"
        if upload and upload.file_info and upload.file_info.data_type:
            data_type_str = upload.file_info.data_type.value if hasattr(upload.file_info.data_type, "value") else str(upload.file_info.data_type)

        sales_items.append(
            SaleItemOut(
                order_id=o.id,
                upload_id=upload.id if upload else 0,
                dataset_title=upload.title if upload else "Licensed Dataset",
                data_type=data_type_str,
                total_amount_paise=o.amount_paise,
                contributor_share_paise=share_paise,
                buyer_email=buyer_email,
                created_at=o.created_at
            )
        )


    # Payout history
    payouts = (
        db.query(PayoutRequest)
        .filter(PayoutRequest.user_id == user_id)
        .order_by(PayoutRequest.created_at.desc())
        .all()
    )
    payout_outs = [PayoutRequestOut.model_validate(p) for p in payouts]

    return ContributorEarningsSummary(
        wallet=WalletOut.model_validate(wallet),
        lifetime_earnings_paise=lifetime_earnings,
        lifetime_withdrawn_paise=lifetime_withdrawn,
        sales_count=len(sales_items),
        recent_sales=sales_items,
        payout_requests=payout_outs
    )

def release_matured_pending_balances(db: Session, user_id: Optional[int] = None) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    wallets_query = db.query(Wallet).filter(Wallet.pending_balance_paise > 0)
    if user_id:
        wallets_query = wallets_query.filter(Wallet.user_id == user_id)

    wallets = wallets_query.all()
    total_released = 0
    affected_users = 0

    for w in wallets:
        amount_to_release = w.pending_balance_paise
        if amount_to_release > 0:
            w.available_balance_paise += amount_to_release
            w.pending_balance_paise = 0
            w.updated_at = now
            total_released += amount_to_release
            affected_users += 1

    db.commit()
    return {
        "released_users_count": affected_users,
        "released_amount_paise": total_released
    }

def request_payout(
    db: Session,
    user_id: int,
    amount_paise: int,
    method: str = "bank_transfer",
    destination: str = ""
) -> PayoutRequest:
    MIN_PAYOUT_PAISE = 1000  # ₹10 or $10 minimum

    if amount_paise < MIN_PAYOUT_PAISE:
        raise ValueError(f"Minimum payout amount is {MIN_PAYOUT_PAISE / 100:.2f} currency units")

    wallet = get_wallet_or_create(db, user_id)
    if wallet.available_balance_paise < amount_paise:
        raise ValueError(
            f"Insufficient available balance. Requested {amount_paise / 100:.2f}, but available is {wallet.available_balance_paise / 100:.2f}"
        )

    # Deduct from available balance
    wallet.available_balance_paise -= amount_paise
    wallet.updated_at = datetime.now(timezone.utc)

    # Create Payout record
    payout = PayoutRequest(
        user_id=user_id,
        amount_paise=amount_paise,
        status=PayoutStatus.REQUESTED,
        method=method,
        destination=destination or "Default Bank Account"
    )
    db.add(payout)
    db.flush()

    # Immutable Ledger Entry: Contributor Payout Debit
    now = datetime.now(timezone.utc)
    ledger_debit = LedgerEntry(
        order_id=None,
        account_type=AccountType.CONTRIBUTOR,
        account_id=user_id,
        amount_paise=amount_paise,
        direction=EntryDirection.DEBIT,
        kind=EntryKind.PAYOUT,
        available_at=now
    )
    db.add(ledger_debit)

    # Audit log
    audit = AuditLog(
        actor_id=user_id,
        action="PAYOUT_REQUESTED",
        entity="payout_request",
        entity_id=str(payout.id),
        meta={"amount_paise": amount_paise, "method": method, "destination": destination}
    )
    db.add(audit)

    db.commit()
    db.refresh(payout)
    return payout

def process_payout_request(
    db: Session,
    payout_id: int,
    action: str, # "complete" or "reject"
    actor_id: int,
    reason: Optional[str] = None
) -> PayoutRequest:
    payout = db.query(PayoutRequest).filter(PayoutRequest.id == payout_id).first()
    if not payout:
        raise ValueError(f"PayoutRequest #{payout_id} not found")

    if payout.status != PayoutStatus.REQUESTED:
        raise ValueError(f"PayoutRequest #{payout_id} is already in '{payout.status}' status")

    now = datetime.now(timezone.utc)

    if action == "complete":
        payout.status = PayoutStatus.COMPLETED
        payout.processed_at = now

        audit = AuditLog(
            actor_id=actor_id,
            action="PAYOUT_COMPLETED",
            entity="payout_request",
            entity_id=str(payout.id),
            meta={"amount_paise": payout.amount_paise}
        )
        db.add(audit)

    elif action == "reject":
        payout.status = PayoutStatus.REJECTED
        payout.processed_at = now

        # Refund back to wallet
        wallet = get_wallet_or_create(db, payout.user_id)
        wallet.available_balance_paise += payout.amount_paise
        wallet.updated_at = now

        # Compensatory Credit Ledger Entry
        refund_entry = LedgerEntry(
            order_id=None,
            account_type=AccountType.CONTRIBUTOR,
            account_id=payout.user_id,
            amount_paise=payout.amount_paise,
            direction=EntryDirection.CREDIT,
            kind=EntryKind.REFUND,
            available_at=now
        )
        db.add(refund_entry)

        audit = AuditLog(
            actor_id=actor_id,
            action="PAYOUT_REJECTED",
            entity="payout_request",
            entity_id=str(payout.id),
            meta={"amount_paise": payout.amount_paise, "reason": reason}
        )
        db.add(audit)
    else:
        raise ValueError(f"Invalid payout action '{action}'. Must be 'complete' or 'reject'")

    db.commit()
    db.refresh(payout)
    return payout
