"""Consent, DPDP compliance, takedown, and data rights API router.

Note: Final legal phrasing of all consent notices and agreements requires formal
review by qualified legal counsel under India's Digital Personal Data Protection
(DPDP) Act, 2023 and DPDP Rules, 2025.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.upload import Upload, UploadStatus
from app.models.listing import Listing, ListingStatus
from app.models.order import Order, License
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
from app.models.audit import Flag, FlagStatus, AuditLog
from app.schemas.consent import (
    ConsentDocumentOut,
    ConsentDocumentCreate,
    ConsentRecordOut,
    ConsentWithdrawRequest,
    TakedownRequestCreate,
    TakedownRequestOut,
    DeletionRequestCreate,
    DeletionRequestOut,
    DataExportOut,
    ConsentReportOut,
)
from app.services.consent.consent_service import ConsentService

router = APIRouter(prefix="/consent", tags=["consent"])


# ── 1. PUBLIC / GENERAL DOCUMENT ACCESS ──────────────────────────────
@router.get("/documents/active", response_model=List[ConsentDocumentOut])
def get_active_consent_documents(db: Session = Depends(get_db)):
    """Fetch all currently active legal and consent documents."""
    docs = ConsentService.get_active_documents(db)
    if not docs:
        ConsentService.seed_default_documents(db)
        docs = ConsentService.get_active_documents(db)
    return docs


@router.get("/documents/{purpose_code}", response_model=ConsentDocumentOut)
def get_document_by_purpose(purpose_code: str, db: Session = Depends(get_db)):
    """Fetch the active version of a specific consent document."""
    doc = ConsentService.get_active_document(db, purpose_code)
    if not doc:
        raise HTTPException(status_code=404, detail=f"No active document for purpose '{purpose_code}'")
    return doc


@router.post("/documents", response_model=ConsentDocumentOut)
def create_document_version(
    payload: ConsentDocumentCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """Admin endpoint to create and activate a new version of a consent document."""
    new_doc = ConsentService.create_or_update_document_version(
        db=db,
        purpose_code=payload.purpose_code,
        title=payload.title,
        body_markdown=payload.body_markdown,
        version=payload.version,
    )
    return new_doc


# ── 2. UPLOAD CONSENT WITHDRAWAL ──────────────────────────────────────
@router.post("/uploads/{upload_id}/withdraw")
def withdraw_upload_consent(
    upload_id: int,
    payload: ConsentWithdrawRequest,
    request: Request,
    current_user: User = Depends(require_roles([UserRole.CONTRIBUTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    Revoke a purpose-specific consent for a dataset.
    - Withdrawing platform_listing_license unpublishes dataset from the marketplace immediately.
    - Withdrawing ai_training_use disables AI training rights for future sales.
    """
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    if upload.contributor_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

    valid_purposes = [
        ConsentPurpose.PLATFORM_LISTING_LICENSE.value,
        ConsentPurpose.AI_TRAINING_USE.value,
    ]
    if payload.purpose_code not in valid_purposes:
        raise HTTPException(
            status_code=400,
            detail=f"Only {valid_purposes} can be individually withdrawn on a per-upload basis.",
        )

    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    rec, effects = ConsentService.withdraw_consent(
        db=db,
        user_id=current_user.id,
        purpose_code=payload.purpose_code,
        upload_id=upload_id,
        ip=ip,
        user_agent=user_agent,
    )

    return {
        "status": "withdrawn",
        "purpose_code": payload.purpose_code,
        "record_id": rec.id,
        "created_at": rec.created_at,
        "effects": effects,
    }


@router.get("/uploads/{upload_id}/records", response_model=List[ConsentRecordOut])
def get_upload_consent_records(
    upload_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve immutable consent transaction records for a specific upload."""
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    if upload.contributor_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

    records = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.upload_id == upload_id)
        .order_by(ConsentRecord.created_at.desc())
        .all()
    )
    return records


# ── 3. PUBLIC TAKEDOWN REQUESTS ──────────────────────────────────────
@router.post("/takedown-requests", response_model=TakedownRequestOut, status_code=status.HTTP_201_CREATED)
def submit_takedown_request(
    payload: TakedownRequestCreate,
    db: Session = Depends(get_db),
):
    """Public submission of copyright, privacy, or unlawful content takedown requests."""
    upload = db.query(Upload).filter(Upload.id == payload.upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Dataset not found")

    takedown = TakedownRequest(
        upload_id=payload.upload_id,
        claimant_name=payload.claimant_name,
        claimant_email=payload.claimant_email,
        reason=payload.reason,
        details=payload.details,
        status=TakedownStatus.PENDING,
    )
    db.add(takedown)

    # Automatically create a moderation flag
    flag = Flag(
        upload_id=payload.upload_id,
        reason=f"Takedown notice ({payload.reason}) by {payload.claimant_name}: {payload.details[:200]}",
        status=FlagStatus.OPEN,
    )
    db.add(flag)
    db.commit()
    db.refresh(takedown)
    return takedown


# ── 4. RIGHT TO ERASURE & DATA EXPORT (DATA PRINCIPAL RIGHTS) ───────
@router.post("/me/deletion-request", response_model=DeletionRequestOut, status_code=status.HTTP_201_CREATED)
def request_account_deletion(
    payload: DeletionRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Initiates an account erasure request under Section 12 of the DPDP Act."""
    existing = (
        db.query(DeletionRequest)
        .filter(
            DeletionRequest.user_id == current_user.id,
            DeletionRequest.status == DeletionRequestStatus.PENDING,
        )
        .first()
    )
    if existing:
        return existing

    req = DeletionRequest(
        user_id=current_user.id,
        reason=payload.reason,
        status=DeletionRequestStatus.PENDING,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("/me/data-export", response_model=DataExportOut)
def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns an export of all user personal data, uploads, transactions,
    and complete immutable consent audit history (Section 11 DPDP Act).
    """
    user_prof = {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role.value,
        "status": current_user.status.value,
        "created_at": current_user.created_at.isoformat(),
        "terms_accepted_version": current_user.terms_accepted_version,
        "privacy_accepted_version": current_user.privacy_accepted_version,
        "is_adult_confirmed": current_user.is_adult_confirmed,
    }
    if current_user.contributor_profile:
        user_prof["contributor_profile"] = {
            "display_name": current_user.contributor_profile.display_name,
            "reputation_score": current_user.contributor_profile.reputation_score,
        }
    if current_user.agency_profile:
        user_prof["agency_profile"] = {
            "company_name": current_user.agency_profile.company_name,
        }

    # Uploads
    uploads = db.query(Upload).filter(Upload.contributor_id == current_user.id).all()
    upload_list = [
        {
            "id": u.id,
            "title": u.title,
            "description": u.description,
            "status": u.status.value,
            "created_at": u.created_at.isoformat(),
            "price_paise": u.price_paise,
            "ai_training_allowed": u.ai_training_allowed,
            "personal_data_status": u.personal_data_status,
            "lawful_basis": u.lawful_basis,
        }
        for u in uploads
    ]

    # Orders & Licenses
    orders = db.query(Order).filter(Order.buyer_id == current_user.id).all()
    order_list = [
        {
            "order_id": o.id,
            "listing_id": o.listing_id,
            "amount_paise": o.amount_paise,
            "status": o.status.value,
            "created_at": o.created_at.isoformat(),
            "license": {
                "terms_version": o.license.terms_version if o.license else None,
                "type": o.license.type if o.license else None,
                "buyer_agreement_sha256": o.license.buyer_agreement_sha256 if o.license else None,
            }
            if o.license
            else None,
        }
        for o in orders
    ]

    # Consent History
    records = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.user_id == current_user.id)
        .order_by(ConsentRecord.created_at.desc())
        .all()
    )
    consent_list = []
    for r in records:
        consent_list.append(
            ConsentRecordOut(
                id=r.id,
                user_id=r.user_id,
                upload_id=r.upload_id,
                order_id=r.order_id,
                purpose_code=r.purpose_code,
                document_id=r.document_id,
                document_sha256=r.document_sha256,
                action=r.action,
                ip=r.ip,
                user_agent=r.user_agent,
                created_at=r.created_at,
                document_title=r.document.title if r.document else None,
                document_version=r.document.version if r.document else None,
            )
        )

    return DataExportOut(
        user_profile=user_prof,
        uploads=upload_list,
        orders_and_licenses=order_list,
        consent_history=consent_list,
        exported_at=datetime.now(timezone.utc),
    )


# ── 5. ADMIN MODERATION, TAKEDOWNS & CONSENT REPORT ──────────────────
@router.get("/admin/takedowns", response_model=List[TakedownRequestOut])
def list_takedowns(
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """Admin review queue for submitted takedowns."""
    return db.query(TakedownRequest).order_by(TakedownRequest.created_at.desc()).all()


@router.post("/admin/takedowns/{takedown_id}/action")
def action_takedown(
    takedown_id: int,
    action: str,  # suspend_listing, dismiss, actioned
    admin_notes: Optional[str] = None,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """Admin actions on a takedown notice: suspend listing, mark actioned, or dismiss."""
    takedown = db.query(TakedownRequest).filter(TakedownRequest.id == takedown_id).first()
    if not takedown:
        raise HTTPException(status_code=404, detail="Takedown request not found")

    upload = db.query(Upload).filter(Upload.id == takedown.upload_id).first()

    if action == "suspend_listing":
        if upload:
            upload.status = UploadStatus.FLAGGED
            if upload.listing:
                upload.listing.status = ListingStatus.INACTIVE
        takedown.status = TakedownStatus.INVESTIGATING
    elif action == "actioned":
        if upload:
            upload.status = UploadStatus.UNPUBLISHED
            if upload.listing:
                upload.listing.status = ListingStatus.INACTIVE
        takedown.status = TakedownStatus.ACTIONED
    elif action == "dismiss":
        takedown.status = TakedownStatus.DISMISSED

    takedown.admin_notes = admin_notes
    db.commit()
    return {"status": takedown.status.value, "admin_notes": admin_notes}


@router.get("/admin/deletions", response_model=List[DeletionRequestOut])
def list_deletions(
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """Admin queue for statutory user erasure requests."""
    return db.query(DeletionRequest).order_by(DeletionRequest.created_at.desc()).all()


@router.post("/admin/deletions/{deletion_id}/approve", response_model=DeletionRequestOut)
def approve_deletion(
    deletion_id: int,
    admin_notes: Optional[str] = "Approved under DPDP Section 12",
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """Executes account erasure, profile anonymization, and listing unpublishing."""
    return ConsentService.process_erasure_request(
        db=db,
        request_id=deletion_id,
        admin_user_id=current_user.id,
        admin_notes=admin_notes,
    )


@router.get("/admin/report", response_model=ConsentReportOut)
def get_consent_report(
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """Consent statistics and DPDP compliance health dashboard."""
    active_docs_count = db.query(ConsentDocument).filter(ConsentDocument.active == True).count()
    total_records = db.query(ConsentRecord).count()

    grants = (
        db.query(ConsentRecord.purpose_code, func.count(ConsentRecord.id))
        .filter(ConsentRecord.action == ConsentAction.GRANTED.value)
        .group_by(ConsentRecord.purpose_code)
        .all()
    )
    grants_by_purpose = {p: c for p, c in grants}

    withdrawals = (
        db.query(ConsentRecord.purpose_code, func.count(ConsentRecord.id))
        .filter(ConsentRecord.action == ConsentAction.WITHDRAWN.value)
        .group_by(ConsentRecord.purpose_code)
        .all()
    )
    withdrawals_by_purpose = {p: c for p, c in withdrawals}

    ai_uploads = db.query(Upload).filter(Upload.ai_training_allowed == True).count()
    awaiting_mod = (
        db.query(Upload)
        .filter(Upload.status.in_([UploadStatus.HELD_UNCATEGORIZED, UploadStatus.FLAGGED]))
        .count()
    )
    pending_takedowns = (
        db.query(TakedownRequest).filter(TakedownRequest.status == TakedownStatus.PENDING).count()
    )
    pending_deletions = (
        db.query(DeletionRequest).filter(DeletionRequest.status == DeletionRequestStatus.PENDING).count()
    )

    return ConsentReportOut(
        total_active_documents=active_docs_count,
        total_records=total_records,
        grants_by_purpose=grants_by_purpose,
        withdrawals_by_purpose=withdrawals_by_purpose,
        uploads_with_ai_training=ai_uploads,
        uploads_awaiting_moderation=awaiting_mod,
        pending_takedowns=pending_takedowns,
        pending_deletions=pending_deletions,
    )
