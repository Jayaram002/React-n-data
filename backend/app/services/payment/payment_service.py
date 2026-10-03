from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.order import Order, OrderStatus, Payment, PaymentStatus, License
from app.models.listing import Listing
from app.models.upload import Upload
from app.models.ledger import LedgerEntry, AccountType, EntryDirection, EntryKind, Wallet
from app.models.audit import AuditLog

# Default dispute window in days (0 in dev/test, 7 in prod)
DISPUTE_WINDOW_DAYS = 0

def process_payment_webhook_event(
    db: Session,
    order_id: int,
    event_status: str, # "paid", "failed", "cancelled"
    provider_ref: Optional[str] = None,
    raw_payload: Optional[Dict[str, Any]] = None
) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise ValueError(f"Order #{order_id} not found")

    # 1. IDEMPOTENCY CHECK:
    # If order is already PAID and another 'paid' event arrives, return existing order safely without double-crediting
    if order.status == OrderStatus.PAID:
        return order

    # 2. Find or create Payment record
    payment = db.query(Payment).filter(Payment.order_id == order.id).first()
    if not payment:
        payment = Payment(
            order_id=order.id,
            provider="mock",
            provider_ref=provider_ref or f"mock_ref_{order_id}",
            status=PaymentStatus.PENDING,
            event_log=[]
        )
        db.add(payment)

    # Append to payment audit log
    event_entry = {
        "event_status": event_status,
        "provider_ref": provider_ref,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": raw_payload or {}
    }
    existing_log = list(payment.event_log or [])
    existing_log.append(event_entry)
    payment.event_log = existing_log

    if event_status == "paid":
        order.status = OrderStatus.PAID
        payment.status = PaymentStatus.COMPLETED

        # 3. 80/20 REVENUE SPLIT CALCULATION (Integer Math)
        total_amount = order.amount_paise
        contributor_amount = (total_amount * 80) // 100
        platform_amount = total_amount - contributor_amount # Any rounding remainder to platform

        upload = order.listing.upload if order.listing else None
        contributor_id = upload.contributor_id if upload else 0

        now = datetime.now(timezone.utc)
        available_at = now + timedelta(days=DISPUTE_WINDOW_DAYS)

        # 4. IMMUTABLE DOUBLE-ENTRY LEDGER
        # Entry A: Buyer Payment Debit (Money outgoing from buyer)
        entry_buyer = LedgerEntry(
            order_id=order.id,
            account_type=AccountType.BUYER,
            account_id=order.buyer_id,
            amount_paise=total_amount,
            direction=EntryDirection.DEBIT,
            kind=EntryKind.BUYER_PAYMENT,
            available_at=now
        )
        db.add(entry_buyer)

        # Entry B: Contributor Credit (80%)
        entry_contributor = LedgerEntry(
            order_id=order.id,
            account_type=AccountType.CONTRIBUTOR,
            account_id=contributor_id,
            amount_paise=contributor_amount,
            direction=EntryDirection.CREDIT,
            kind=EntryKind.CONTRIBUTOR_CREDIT,
            available_at=available_at
        )
        db.add(entry_contributor)

        # Entry C: Platform Fee Credit (20%)
        entry_platform = LedgerEntry(
            order_id=order.id,
            account_type=AccountType.PLATFORM,
            account_id=0, # Platform account
            amount_paise=platform_amount,
            direction=EntryDirection.CREDIT,
            kind=EntryKind.PLATFORM_FEE,
            available_at=now
        )
        db.add(entry_platform)

        # 5. UPDATE CONTRIBUTOR WALLET
        wallet = db.query(Wallet).filter(Wallet.user_id == contributor_id).first()
        if not wallet:
            wallet = Wallet(user_id=contributor_id, pending_balance_paise=0, available_balance_paise=0)
            db.add(wallet)

        if DISPUTE_WINDOW_DAYS > 0:
            wallet.pending_balance_paise += contributor_amount
        else:
            wallet.available_balance_paise += contributor_amount
        wallet.updated_at = now

        # 6. ISSUE LICENSE RECORD
        existing_license = db.query(License).filter(License.order_id == order.id).first()
        if not existing_license:
            license_record = License(
                order_id=order.id,
                terms_version="1.0",
                type="non_exclusive_commercial"
            )
            db.add(license_record)

        # 7. WRITE AUDIT LOG
        audit = AuditLog(
            actor_id=order.buyer_id,
            action="ORDER_PAID",
            entity="order",
            entity_id=str(order.id),
            meta={
                "amount_paise": total_amount,
                "contributor_amount": contributor_amount,
                "platform_amount": platform_amount,
                "contributor_id": contributor_id
            }
        )
        db.add(audit)

    elif event_status == "failed":
        order.status = OrderStatus.FAILED
        payment.status = PaymentStatus.FAILED

    elif event_status == "cancelled":
        order.status = OrderStatus.CANCELLED
        payment.status = PaymentStatus.FAILED

    db.commit()
    db.refresh(order)
    return order
