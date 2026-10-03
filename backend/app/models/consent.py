"""Consent framework models designed for India's DPDP Act/Rules 2025.

Note: Final legal phrasing of all consent notices and agreements requires formal
review by qualified legal counsel under India's Digital Personal Data Protection
(DPDP) Act, 2023 and DPDP Rules, 2025.
"""

from datetime import datetime, timezone
import enum
import hashlib
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Enum,
    ForeignKey,
    Boolean,
    Index,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class ConsentPurpose(str, enum.Enum):
    TERMS_OF_SERVICE = "terms_of_service"
    PRIVACY_NOTICE = "privacy_notice"
    CONTRIBUTOR_RIGHTS_WARRANTY = "contributor_rights_warranty"
    THIRD_PARTY_DATA_ATTESTATION = "third_party_data_attestation"
    PLATFORM_LISTING_LICENSE = "platform_listing_license"
    AI_TRAINING_USE = "ai_training_use"
    BUYER_LICENSE_AGREEMENT = "buyer_license_agreement"


class ConsentAction(str, enum.Enum):
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"


class PersonalDataStatus(str, enum.Enum):
    NONE = "none"
    ANONYMIZED = "anonymized"
    CONTAINS_PERSONAL_DATA = "contains_personal_data"


class DeletionRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TakedownStatus(str, enum.Enum):
    PENDING = "pending"
    INVESTIGATING = "investigating"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class ConsentDocument(Base):
    """
    Versioned, immutable legal and consent documents.
    Edits must create a new version with an updated SHA256 checksum.
    """
    __tablename__ = "consent_documents"

    id = Column(Integer, primary_key=True, index=True)
    purpose_code = Column(String(64), nullable=False, index=True)
    version = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)
    body_markdown = Column(Text, nullable=False)
    sha256 = Column(String(64), nullable=False)
    effective_from = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_consent_docs_purpose_version", "purpose_code", "version", unique=True),
    )

    @staticmethod
    def calculate_sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ConsentRecord(Base):
    """
    Append-only, immutable consent journal.
    No records are ever updated or deleted.
    Withdrawals are recorded as new rows with action='withdrawn'.
    Current status resolves from the latest record for a given purpose.
    On user erasure, user_id is set to NULL/anonymized but the record is preserved.
    """
    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    upload_id = Column(
        Integer,
        ForeignKey("uploads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    purpose_code = Column(String(64), nullable=False, index=True)
    document_id = Column(
        Integer,
        ForeignKey("consent_documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    document_sha256 = Column(String(64), nullable=False)
    action = Column(String(20), default=ConsentAction.GRANTED.value, nullable=False)
    ip = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    document = relationship("ConsentDocument")
    user = relationship("User", foreign_keys=[user_id])
    upload = relationship("Upload", foreign_keys=[upload_id])
    order = relationship("Order", foreign_keys=[order_id])

    __table_args__ = (
        Index("ix_consent_records_user_purpose_date", "user_id", "purpose_code", "created_at"),
        Index("ix_consent_records_upload_purpose", "upload_id", "purpose_code"),
    )


class TakedownRequest(Base):
    """
    Publicly submitted copyright or privacy takedown notices.
    """
    __tablename__ = "takedown_requests"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(
        Integer,
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claimant_name = Column(String(255), nullable=False)
    claimant_email = Column(String(255), nullable=False)
    reason = Column(String(100), nullable=False)  # copyright, pii_violation, unlawful
    details = Column(Text, nullable=False)
    status = Column(
        Enum(TakedownStatus),
        default=TakedownStatus.PENDING,
        nullable=False,
        index=True,
    )
    admin_notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    upload = relationship("Upload", foreign_keys=[upload_id])


class DeletionRequest(Base):
    """
    Data Principal right to erasure / account deletion request under DPDP Act.
    """
    __tablename__ = "deletion_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(DeletionRequestStatus),
        default=DeletionRequestStatus.PENDING,
        nullable=False,
        index=True,
    )
    reason = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
