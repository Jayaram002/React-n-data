"""Consent Management & DPDP Compliance Engine.

Note: Final legal phrasing of all consent notices and agreements requires formal
review by qualified legal counsel under India's Digital Personal Data Protection
(DPDP) Act, 2023 and DPDP Rules, 2025.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.consent import (
    ConsentDocument,
    ConsentRecord,
    ConsentPurpose,
    ConsentAction,
    TakedownRequest,
    DeletionRequest,
    DeletionRequestStatus,
    TakedownStatus,
)
from app.models.upload import Upload, UploadStatus
from app.models.listing import Listing, ListingStatus
from app.models.order import Order, License
from app.models.user import User, UserStatus
from app.models.audit import AuditLog, Flag, FlagStatus

# Default Plain-Language Consent Documents (v1.0)
DEFAULT_DOCUMENTS: List[Dict[str, str]] = [
    {
        "purpose_code": ConsentPurpose.TERMS_OF_SERVICE.value,
        "version": "1.0",
        "title": "Platform Terms of Service",
        "body_markdown": """# React n Data — Platform Terms of Service (v1.0)

*Last Updated: 2026-10-01 • Effective Date: Immediate*

### 1. Intermediary Status
React n Data operates as an electronic marketplace and data intermediary connecting qualified contributors with commercial data procurement entities. All transactions are governed by the Information Technology Act, 2000 and Digital Personal Data Protection Act, 2023.

### 2. Contributor Responsibilities
Contributors must possess verified ownership, intellectual property rights, or explicit authorization to monetize uploaded datasets. Contributor payouts are processed on an 80/20 platform ledger basis subject to mandatory dispute settlement windows.

### 3. Buyer Permitted Uses
Data buyers are granted non-exclusive, non-sublicensable commercial use licenses. Re-identification, reverse-engineering of anonymized data subjects, and unsolicited marketing are strictly prohibited.

### 4. Grievance Redressal
Any consumer or contributor disputes may be escalated directly to our designated Grievance Officer in compliance with Indian regulatory directives.
""",
    },
    {
        "purpose_code": ConsentPurpose.PRIVACY_NOTICE.value,
        "version": "1.0",
        "title": "Privacy Notice & Data Fiduciary Obligations",
        "body_markdown": """# Privacy Notice & Notice to Data Principals (v1.0)

*Prescribed under Section 5 of India's Digital Personal Data Protection Act, 2023*

### 1. Data Fiduciary Identity
React n Data Technologies Private Limited operates as the Data Fiduciary regarding user identity, account management, and marketplace transactions.

### 2. Specific Purposes for Processing
- Verification of Contributor authenticity and identity
- Facilitation of commercial payment settlements and ledger administration
- Delivery of immutable cryptographic proofs of dataset licensing

### 3. Your Rights as a Data Principal
Under DPDP Rules 2025, you hold statutory rights to:
- Access summaries of your personal data and processing activities
- Request correction, completion, and updating of inaccurate data
- Seek erasure of your personal data subject to mandatory statutory tax and ledger retention obligations (7 years)
- Register formal grievances with our Grievance Redressal Officer
""",
    },
    {
        "purpose_code": ConsentPurpose.CONTRIBUTOR_RIGHTS_WARRANTY.value,
        "version": "1.0",
        "title": "Contributor Rights & Intellectual Property Warranty",
        "body_markdown": """# Contributor Rights & IP Warranty (v1.0)

I explicitly warrant, represent, and guarantee to React n Data and its buyers:
1. **Ownership & Title:** I am the lawful creator, copyright holder, or authorized licensor of the submitted dataset.
2. **Non-Infringement:** The dataset does not infringe upon any third-party patent, trademark, copyright, trade secret, or proprietary entitlement.
3. **No Unlawful Interception:** The data was gathered without illegal wiretapping, computer breach, or breach of fiduciary confidentiality agreements.
""",
    },
    {
        "purpose_code": ConsentPurpose.THIRD_PARTY_DATA_ATTESTATION.value,
        "version": "1.0",
        "title": "Personal Data Status & Lawful Basis Attestation",
        "body_markdown": """# Personal Data & DPDP Attestation (v1.0)

In compliance with India's DPDP Act, 2023:
- **No Unconsented Personal Data:** If the dataset contains personal identifiers of individuals, I hold unambiguous, freely given, specific, and informed consent or a verified statutory lawful basis.
- **Anonymization Standard:** Datasets marked 'anonymized' have undergone irreversible obfuscation such that individual data subjects cannot be identified with reasonable technical effort.
- **Audit Cooperation:** I agree to furnish proof of lawful basis to Platform Compliance Administrators upon request.
""",
    },
    {
        "purpose_code": ConsentPurpose.PLATFORM_LISTING_LICENSE.value,
        "version": "1.0",
        "title": "Platform Hosting & Commercial Listing License",
        "body_markdown": """# Platform Distribution & Listing License (v1.0)

I grant React n Data a worldwide, revocable, non-exclusive license to:
1. Store and encrypt raw dataset artifacts on secure infrastructure.
2. Generate watermarked low-resolution previews and schema extracts.
3. Ingest sample records into automated Gemma AI quality scoring and taxonomy engines.
4. Distribute non-exclusive commercial licenses to verified enterprise buyers.

*Revocation Note:* Withdrawing this license unpublishes the dataset from public marketplace discovery immediately. Prior commercial licenses acquired by buyers remain binding.
""",
    },
    {
        "purpose_code": ConsentPurpose.AI_TRAINING_USE.value,
        "version": "1.0",
        "title": "Permitted Machine Learning & AI Training Grant",
        "body_markdown": """# Machine Learning & AI Foundation Model Training Grant (v1.0)

*(Optional Purpose-Specific Consent)*

I explicitly grant permission for buyers of this dataset to utilize the records to train, fine-tune, align, and evaluate artificial intelligence and machine learning models, including large multimodal models.

*Revocation Note:* You may revoke this permission at any time. Revocation disables AI training rights for future buyers.
""",
    },
    {
        "purpose_code": ConsentPurpose.BUYER_LICENSE_AGREEMENT.value,
        "version": "1.0",
        "title": "Commercial Data Buyer License Agreement",
        "body_markdown": """# Commercial Buyer License Agreement (v1.0)

By acquiring this dataset license, the purchasing entity covenants:
1. **Grant:** Non-exclusive, non-transferable, perpetual commercial use license.
2. **Prohibited Resale:** Direct sub-licensing, syndication, or raw resale of the dataset is strictly prohibited.
3. **No Re-Identification:** The Buyer strictly covenants never to attempt re-identification of anonymized individuals.
4. **AI Training Restriction:** Machine learning training is permitted strictly if the listing indicates AI Training Grant is active.
""",
    },
]


class ConsentService:
    """Manages legal documents, consent journals, withdrawals, and erasure workflows."""

    @staticmethod
    def seed_default_documents(db: Session) -> int:
        """Seed initial v1.0 documents if missing."""
        seeded_count = 0
        for doc_def in DEFAULT_DOCUMENTS:
            existing = (
                db.query(ConsentDocument)
                .filter(
                    ConsentDocument.purpose_code == doc_def["purpose_code"],
                    ConsentDocument.version == doc_def["version"],
                )
                .first()
            )
            if not existing:
                sha256 = ConsentDocument.calculate_sha256(doc_def["body_markdown"])
                doc = ConsentDocument(
                    purpose_code=doc_def["purpose_code"],
                    version=doc_def["version"],
                    title=doc_def["title"],
                    body_markdown=doc_def["body_markdown"],
                    sha256=sha256,
                    effective_from=datetime.now(timezone.utc),
                    active=True,
                )
                db.add(doc)
                seeded_count += 1
        if seeded_count > 0:
            db.commit()
        return seeded_count

    @staticmethod
    def get_active_documents(db: Session) -> List[ConsentDocument]:
        """Fetch all currently active consent documents."""
        return (
            db.query(ConsentDocument)
            .filter(ConsentDocument.active == True)
            .order_by(ConsentDocument.purpose_code.asc())
            .all()
        )

    @staticmethod
    def get_active_document(db: Session, purpose_code: str) -> Optional[ConsentDocument]:
        """Fetch active document for a purpose code."""
        return (
            db.query(ConsentDocument)
            .filter(
                ConsentDocument.purpose_code == purpose_code,
                ConsentDocument.active == True,
            )
            .order_by(ConsentDocument.id.desc())
            .first()
        )

    @staticmethod
    def create_or_update_document_version(
        db: Session,
        purpose_code: str,
        title: str,
        body_markdown: str,
        version: str,
    ) -> ConsentDocument:
        """
        Creates a new immutable version of a consent document and deactivates prior versions.
        """
        # Deactivate older versions of this purpose
        db.query(ConsentDocument).filter(
            ConsentDocument.purpose_code == purpose_code,
            ConsentDocument.active == True,
        ).update({"active": False})

        sha256 = ConsentDocument.calculate_sha256(body_markdown)
        doc = ConsentDocument(
            purpose_code=purpose_code,
            version=version,
            title=title,
            body_markdown=body_markdown,
            sha256=sha256,
            effective_from=datetime.now(timezone.utc),
            active=True,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def record_consent(
        db: Session,
        user_id: Optional[int],
        purpose_code: str,
        action: str = ConsentAction.GRANTED.value,
        upload_id: Optional[int] = None,
        order_id: Optional[int] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        document_id: Optional[int] = None,
        document_sha256: Optional[str] = None,
    ) -> ConsentRecord:
        """
        Appends an immutable consent transaction record.
        """
        if not document_id or not document_sha256:
            active_doc = ConsentService.get_active_document(db, purpose_code)
            if not active_doc:
                raise ValueError(f"No active consent document found for purpose '{purpose_code}'")
            doc_id = active_doc.id
            doc_sha = active_doc.sha256
            doc_ver = active_doc.version
        else:
            doc_id = document_id
            doc_sha = document_sha256
            doc_ver = "1.0"

        rec = ConsentRecord(
            user_id=user_id,
            upload_id=upload_id,
            order_id=order_id,
            purpose_code=purpose_code,
            document_id=doc_id,
            document_sha256=doc_sha,
            action=action,
            ip=ip,
            user_agent=user_agent,
            created_at=datetime.now(timezone.utc),
        )
        db.add(rec)

        # Audit log change
        log = AuditLog(
            actor_id=user_id,
            action=f"CONSENT_{action.upper()}",
            entity="consent_record",
            entity_id=str(doc_id),
            meta={"purpose_code": purpose_code, "version": doc_ver, "action": action},
        )
        db.add(log)
        db.commit()
        db.refresh(rec)
        return rec

    @staticmethod
    def get_consent_status(
        db: Session,
        user_id: int,
        purpose_code: str,
        upload_id: Optional[int] = None,
        order_id: Optional[int] = None
    ) -> Optional[str]:
        """Resolves current consent status from latest immutable row."""
        q = db.query(ConsentRecord).filter(
            ConsentRecord.user_id == user_id,
            ConsentRecord.purpose_code == purpose_code
        )
        if upload_id is not None:
            q = q.filter(ConsentRecord.upload_id == upload_id)
        if order_id is not None:
            q = q.filter(ConsentRecord.order_id == order_id)
        latest = q.order_by(ConsentRecord.created_at.desc(), ConsentRecord.id.desc()).first()
        return latest.action if latest else None

    @staticmethod
    def has_active_consent(
        db: Session,
        user_id: int,
        purpose_code: str,
        upload_id: Optional[int] = None,
    ) -> bool:
        """
        Resolves latest status for (user, purpose, upload): returns True if latest row is 'granted'.
        """
        query = db.query(ConsentRecord).filter(
            ConsentRecord.user_id == user_id,
            ConsentRecord.purpose_code == purpose_code,
        )
        if upload_id is not None:
            query = query.filter(ConsentRecord.upload_id == upload_id)

        latest = query.order_by(ConsentRecord.id.desc()).first()
        return bool(latest and latest.action == ConsentAction.GRANTED.value)

    @staticmethod
    def withdraw_consent(
        db: Session,
        user_id: int,
        purpose_code: str,
        upload_id: Optional[int] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[ConsentRecord, Dict[str, Any]]:
        """
        Withdraws consent by appending an immutable 'withdrawn' record.
        Handles cascading side-effects:
        - If platform_listing_license is withdrawn: unpublishes the upload and listing immediately.
        - If ai_training_use is withdrawn: turns off ai_training_allowed for future sales.
        """
        # Append withdrawal row
        rec = ConsentService.record_consent(
            db=db,
            user_id=user_id,
            purpose_code=purpose_code,
            action=ConsentAction.WITHDRAWN.value,
            upload_id=upload_id,
            ip=ip,
            user_agent=user_agent,
        )

        effects = {}
        if upload_id:
            upload = db.query(Upload).filter(Upload.id == upload_id).first()
            if upload:
                if purpose_code == ConsentPurpose.PLATFORM_LISTING_LICENSE.value:
                    upload.status = UploadStatus.UNPUBLISHED
                    if upload.listing:
                        upload.listing.status = ListingStatus.INACTIVE
                    effects["listing_unpublished"] = True
                    effects["message"] = (
                        "Platform listing license withdrawn. Dataset has been unpublished from marketplace immediately. "
                        "Existing acquired licenses and earnings remain valid."
                    )
                elif purpose_code == ConsentPurpose.AI_TRAINING_USE.value:
                    upload.ai_training_allowed = False
                    effects["ai_training_disabled"] = True
                    effects["message"] = (
                        "AI training consent revoked. Future buyers will not receive AI training licenses."
                    )
                db.commit()

        return rec, effects

    @staticmethod
    def backfill_legacy_consents(db: Session) -> int:
        """
        Backfill existing uploads that have consent_version/consent_at into the new consent_records table.
        """
        ConsentService.seed_default_documents(db)
        rights_doc = ConsentService.get_active_document(db, ConsentPurpose.CONTRIBUTOR_RIGHTS_WARRANTY.value)
        license_doc = ConsentService.get_active_document(db, ConsentPurpose.PLATFORM_LISTING_LICENSE.value)
        ai_doc = ConsentService.get_active_document(db, ConsentPurpose.AI_TRAINING_USE.value)

        uploads = db.query(Upload).all()
        created = 0
        for u in uploads:
            # Check if record already exists
            existing = (
                db.query(ConsentRecord)
                .filter(
                    ConsentRecord.upload_id == u.id,
                    ConsentRecord.purpose_code == ConsentPurpose.CONTRIBUTOR_RIGHTS_WARRANTY.value,
                )
                .first()
            )
            if not existing and rights_doc:
                db.add(
                    ConsentRecord(
                        user_id=u.contributor_id,
                        upload_id=u.id,
                        purpose_code=ConsentPurpose.CONTRIBUTOR_RIGHTS_WARRANTY.value,
                        document_id=rights_doc.id,
                        document_sha256=rights_doc.sha256,
                        action=ConsentAction.GRANTED.value,
                        created_at=u.consent_at or u.created_at,
                    )
                )
                created += 1

            existing_lic = (
                db.query(ConsentRecord)
                .filter(
                    ConsentRecord.upload_id == u.id,
                    ConsentRecord.purpose_code == ConsentPurpose.PLATFORM_LISTING_LICENSE.value,
                )
                .first()
            )
            if not existing_lic and license_doc:
                db.add(
                    ConsentRecord(
                        user_id=u.contributor_id,
                        upload_id=u.id,
                        purpose_code=ConsentPurpose.PLATFORM_LISTING_LICENSE.value,
                        document_id=license_doc.id,
                        document_sha256=license_doc.sha256,
                        action=ConsentAction.GRANTED.value,
                        created_at=u.consent_at or u.created_at,
                    )
                )
                created += 1

            if u.ai_training_allowed and ai_doc:
                existing_ai = (
                    db.query(ConsentRecord)
                    .filter(
                        ConsentRecord.upload_id == u.id,
                        ConsentRecord.purpose_code == ConsentPurpose.AI_TRAINING_USE.value,
                    )
                    .first()
                )
                if not existing_ai:
                    db.add(
                        ConsentRecord(
                            user_id=u.contributor_id,
                            upload_id=u.id,
                            purpose_code=ConsentPurpose.AI_TRAINING_USE.value,
                            document_id=ai_doc.id,
                            document_sha256=ai_doc.sha256,
                            action=ConsentAction.GRANTED.value,
                            created_at=u.consent_at or u.created_at,
                        )
                    )
                    created += 1

        if created > 0:
            db.commit()
        return created

    @staticmethod
    def process_erasure_request(db: Session, request_id: int, admin_user_id: int, admin_notes: str = "") -> DeletionRequest:
        """
        Executes right to erasure (Section 12 DPDP Act 2023):
        - Unpublishes all contributor listings
        - Anonymizes user profile & email
        - Preserves immutable financial ledger entries and consent records (anonymized user link)
        """
        del_req = db.query(DeletionRequest).filter(DeletionRequest.id == request_id).first()
        if not del_req:
            raise ValueError("Deletion request not found")

        user = db.query(User).filter(User.id == del_req.user_id).first()
        if not user:
            raise ValueError("User not found")

        # 1. Unpublish all uploads & listings
        uploads = db.query(Upload).filter(Upload.contributor_id == user.id).all()
        for u in uploads:
            u.status = UploadStatus.UNPUBLISHED
            if u.listing:
                u.listing.status = ListingStatus.INACTIVE

        # 2. Anonymize user profile
        uid = user.id
        user.email = f"anonymized_user_{uid}@redacted.local"
        user.password_hash = "DELETED_USER_HASH"
        user.status = UserStatus.SUSPENDED
        user.deleted_at = datetime.now(timezone.utc)

        if user.contributor_profile:
            user.contributor_profile.display_name = f"Former Contributor #{uid}"
        if user.agency_profile:
            user.agency_profile.company_name = f"Former Agency #{uid}"

        # 3. Mark deletion request as approved
        del_req.status = DeletionRequestStatus.APPROVED
        del_req.processed_at = datetime.now(timezone.utc)
        del_req.admin_notes = admin_notes

        # 4. Audit log
        db.add(
            AuditLog(
                actor_id=admin_user_id,
                action="ERASURE_APPROVED",
                entity="user",
                entity_id=str(uid),
                meta={"details": f"Right to erasure executed for user #{uid}. Profile anonymized. Consent records & ledger retained for statutory compliance."},
            )
        )
        db.commit()
        db.refresh(del_req)
        return del_req
