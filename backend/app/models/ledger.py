from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class AccountType(str, enum.Enum):
    CONTRIBUTOR = "contributor"
    PLATFORM = "platform"
    BUYER = "buyer"

class EntryDirection(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"

class EntryKind(str, enum.Enum):
    BUYER_PAYMENT = "buyer_payment"
    CONTRIBUTOR_CREDIT = "contributor_credit"
    PLATFORM_FEE = "platform_fee"
    REFUND = "refund"
    PAYOUT = "payout"

class PayoutStatus(str, enum.Enum):
    REQUESTED = "requested"
    COMPLETED = "completed"
    REJECTED = "rejected"

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    account_type = Column(Enum(AccountType), nullable=False)
    account_id = Column(Integer, nullable=False, index=True) # user_id or 0 for platform
    amount_paise = Column(Integer, nullable=False)
    direction = Column(Enum(EntryDirection), nullable=False)
    kind = Column(Enum(EntryKind), nullable=False)
    available_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class Wallet(Base):
    __tablename__ = "wallets"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    pending_balance_paise = Column(Integer, default=0, nullable=False)
    available_balance_paise = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="wallet")

class PayoutRequest(Base):
    __tablename__ = "payout_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount_paise = Column(Integer, nullable=False)
    status = Column(Enum(PayoutStatus), default=PayoutStatus.REQUESTED, nullable=False)
    method = Column(String, default="bank_transfer", nullable=True)
    destination = Column(String, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", foreign_keys=[user_id])

