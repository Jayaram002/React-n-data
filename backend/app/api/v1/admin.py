import math
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.upload import Upload, UploadStatus, CategorySource
from app.models.category import Category
from app.models.listing import Listing, ListingStatus
from app.models.order import Order, OrderStatus, License
from app.models.ledger import LedgerEntry, PayoutRequest, AccountType, EntryDirection, EntryKind, PayoutStatus
from app.models.audit import Flag, FlagStatus, AuditLog
from app.schemas.admin import (
    ModerationItemOut, ModerationActionIn, FlagResolveIn,
    AdminCategoryCreate, AdminCategoryUpdate,
    AdminSubcategoryCreate, AdminSubcategoryUpdate,
    PlatformAnalyticsOut, AuditLogOut, AuditLogPagination
)
from app.schemas.category import CategoryTreeOut, SubcategoryOut
from app.services.pricing import calculate_suggested_price




router = APIRouter(prefix="/admin", tags=["admin"])

# ==========================================
# 1. MODERATION QUEUE & FLAG RESOLUTION
# ==========================================

@router.get("/moderation/queue", response_model=List[ModerationItemOut])
def get_moderation_queue(
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    # Retrieve uploads that are FLAGGED, HELD_UNCATEGORIZED, or have open flags
    uploads = (
        db.query(Upload)
        .outerjoin(Flag, Flag.upload_id == Upload.id)
        .filter(
            or_(
                Upload.status.in_([UploadStatus.FLAGGED, UploadStatus.HELD_UNCATEGORIZED]),
                Upload.category_source == CategorySource.CONTRIBUTOR,
                and_(Flag.status == FlagStatus.OPEN)
            )
        )
        .distinct()
        .order_by(Upload.created_at.desc())
        .all()
    )

    from app.models.consent import ConsentRecord
    from app.services.storage import get_storage_service

    items = []
    for u in uploads:
        flags = db.query(Flag).filter(Flag.upload_id == u.id, Flag.status == FlagStatus.OPEN).all()
        flags_data = [{"id": f.id, "reason": f.reason, "source": f.source, "created_at": f.created_at.isoformat()} for f in flags]

        contributor_name = "Contributor"
        if u.contributor and u.contributor.contributor_profile:
            contributor_name = u.contributor.contributor_profile.display_name

        data_type_str = "tabular"
        if u.file_info and u.file_info.data_type:
            data_type_str = u.file_info.data_type.value if hasattr(u.file_info.data_type, "value") else str(u.file_info.data_type)

        score = u.ai_analysis.total_score if u.ai_analysis else None

        # Fetch consent history for this upload
        consent_recs = (
            db.query(ConsentRecord)
            .filter(ConsentRecord.upload_id == u.id)
            .order_by(ConsentRecord.created_at.desc())
            .all()
        )
        consent_data = [
            {
                "purpose_code": cr.purpose_code,
                "action": cr.action,
                "created_at": cr.created_at.isoformat(),
                "document_sha256": cr.document_sha256[:10] + "..." if cr.document_sha256 else "",
                "ip": cr.ip
            }
            for cr in consent_recs
        ]

        has_ev = bool(u.evidence_storage_key)
        ev_url = f"/api/v1/admin/uploads/{u.id}/evidence" if has_ev else None

        items.append(
            ModerationItemOut(
                id=u.id,
                contributor_id=u.contributor_id,
                contributor_email=u.contributor.email if u.contributor else "unknown",
                contributor_name=contributor_name,
                title=u.title,
                description=u.description,
                status=u.status,
                category_id=u.category_id,
                category_name=u.category.name if u.category else None,
                subcategory_id=u.subcategory_id,
                subcategory_name=u.subcategory.name if u.subcategory else None,
                category_source=u.category_source,
                category_confidence=u.category_confidence,
                price_paise=u.price_paise,
                data_type=data_type_str,
                flags_count=len(flags),
                open_flags=flags_data,
                ai_total_score=score,
                personal_data_status=u.personal_data_status or "none",
                lawful_basis=u.lawful_basis,
                lawful_basis_note=u.lawful_basis_note,
                has_evidence=has_ev,
                evidence_download_url=ev_url,
                consent_records=consent_data,
                created_at=u.created_at
            )
        )

    return items

@router.get("/uploads/{upload_id}/evidence")
def download_evidence_file(
    upload_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    from fastapi import Response
    from app.services.storage import get_storage_service

    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload or not upload.evidence_storage_key:
        raise HTTPException(status_code=404, detail="No evidence file found for this upload")

    storage_service = get_storage_service()
    try:
        data = storage_service.get_file(upload.evidence_storage_key)
    except Exception:
        raise HTTPException(status_code=404, detail="Evidence file missing in storage")

    ext = upload.evidence_storage_key.split(".")[-1] if "." in upload.evidence_storage_key else "bin"
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="evidence_upload_{upload_id}.{ext}"'}
    )

@router.post("/moderation/uploads/{upload_id}/action", response_model=Dict[str, Any])
def execute_moderation_action(
    upload_id: int,
    action_in: ModerationActionIn,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

    action = action_in.action.lower()
    now = datetime.now(timezone.utc)

    if action in ("approve", "assign_category"):
        if action_in.category_id:
            category = db.query(Category).filter(Category.id == action_in.category_id).first()
            if not category:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
            upload.category_id = category.id
            upload.subcategory_id = action_in.subcategory_id
            upload.category_source = CategorySource.ADMIN
            upload.category_confidence = 1.0

            # Recalculate price bounds with new category base price
            base_price = category.base_price_paise
            if action_in.subcategory_id:
                sub = db.query(Category).filter(Category.id == action_in.subcategory_id).first()
                if sub and sub.base_price_paise:
                    base_price = sub.base_price_paise

            trust_score = upload.ai_analysis.total_score if upload.ai_analysis else 80.0
            pricing = calculate_suggested_price(base_price, trust_score)
            upload.price_paise = pricing["suggested_price_paise"]
            upload.ai_min_price = pricing["ai_min_price_paise"]
            upload.ai_max_price = pricing["ai_max_price_paise"]

        upload.status = UploadStatus.ANALYZED

        # Resolve open flags on this upload
        db.query(Flag).filter(Flag.upload_id == upload.id, Flag.status == FlagStatus.OPEN).update({
            "status": FlagStatus.RESOLVED,
            "resolved_by": current_user.id
        })

    elif action == "flag":
        upload.status = UploadStatus.FLAGGED
        flag = Flag(
            upload_id=upload.id,
            reason=action_in.reason or "Flagged by Admin moderation",
            source="admin",
            status=FlagStatus.OPEN
        )
        db.add(flag)

        # Deactivate listing if active
        if upload.listing:
            upload.listing.status = ListingStatus.INACTIVE

    elif action == "request_evidence":
        upload.status = UploadStatus.FLAGGED
        flag = Flag(
            upload_id=upload.id,
            reason=action_in.reason or "Admin requested evidence of lawful basis / consent documentation",
            source="admin",
            status=FlagStatus.OPEN
        )
        db.add(flag)
        if upload.listing:
            upload.listing.status = ListingStatus.INACTIVE

    elif action == "reject":
        upload.status = UploadStatus.REJECTED
        if upload.listing:
            upload.listing.status = ListingStatus.INACTIVE

    elif action == "unpublish":
        upload.status = UploadStatus.UNPUBLISHED
        if upload.listing:
            upload.listing.status = ListingStatus.INACTIVE
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid action '{action}'")

    # Audit log
    audit = AuditLog(
        actor_id=current_user.id,
        action=f"ADMIN_MODERATION_{action.upper()}",
        entity="upload",
        entity_id=str(upload.id),
        meta={"reason": action_in.reason, "category_id": action_in.category_id}
    )
    db.add(audit)
    db.commit()
    db.refresh(upload)

    return {"status": "success", "action": action, "upload_id": upload.id, "upload_status": upload.status.value}

@router.post("/flags/{flag_id}/resolve", response_model=Dict[str, Any])
def resolve_flag(
    flag_id: int,
    resolve_in: FlagResolveIn,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    flag = db.query(Flag).filter(Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    action = resolve_in.action.lower()
    if action == "resolve":
        flag.status = FlagStatus.RESOLVED
    elif action == "dismiss":
        flag.status = FlagStatus.DISMISSED
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be 'resolve' or 'dismiss'")

    flag.resolved_by = current_user.id

    # If all flags on the upload are now resolved/dismissed, and status was FLAGGED, restore to ANALYZED
    remaining_flags = db.query(Flag).filter(Flag.upload_id == flag.upload_id, Flag.status == FlagStatus.OPEN).count()
    if remaining_flags == 0 and flag.upload and flag.upload.status == UploadStatus.FLAGGED:
        flag.upload.status = UploadStatus.ANALYZED

    audit = AuditLog(
        actor_id=current_user.id,
        action=f"FLAG_{action.upper()}",
        entity="flag",
        entity_id=str(flag.id),
        meta={"notes": resolve_in.notes, "upload_id": flag.upload_id}
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "flag_id": flag.id, "flag_status": flag.status.value}

# ==========================================
# 2. TAXONOMY MANAGER CRUD
# ==========================================

@router.post("/taxonomy/categories", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_domain_category(
    cat_in: AdminCategoryCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    existing = db.query(Category).filter(Category.slug == cat_in.slug.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Category slug '{cat_in.slug}' already exists")

    cat = Category(
        parent_id=None,
        name=cat_in.name,
        slug=cat_in.slug.lower().replace(" ", "-"),
        base_price_paise=cat_in.base_price_paise,
        active=cat_in.active,
        version=1
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)

    db.add(AuditLog(actor_id=current_user.id, action="CATEGORY_CREATED", entity="category", entity_id=str(cat.id), meta={"slug": cat.slug, "name": cat.name}))
    db.commit()

    return {"id": cat.id, "name": cat.name, "slug": cat.slug, "base_price_paise": cat.base_price_paise, "active": cat.active}

@router.patch("/taxonomy/categories/{category_id}", response_model=Dict[str, Any])
def update_domain_category(
    category_id: int,
    cat_in: AdminCategoryUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if cat_in.name is not None:
        cat.name = cat_in.name
    if cat_in.slug is not None:
        cat.slug = cat_in.slug.lower().replace(" ", "-")
    if cat_in.base_price_paise is not None:
        cat.base_price_paise = cat_in.base_price_paise
    if cat_in.active is not None:
        cat.active = cat_in.active

    cat.version += 1
    db.add(AuditLog(actor_id=current_user.id, action="CATEGORY_UPDATED", entity="category", entity_id=str(cat.id), meta={"name": cat.name, "base_price_paise": cat.base_price_paise}))
    db.commit()
    db.refresh(cat)

    return {"id": cat.id, "name": cat.name, "slug": cat.slug, "base_price_paise": cat.base_price_paise, "active": cat.active, "version": cat.version}

@router.post("/taxonomy/subcategories", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_subcategory(
    sub_in: AdminSubcategoryCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    parent = db.query(Category).filter(Category.id == sub_in.parent_id).first()
    if not parent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent category not found")

    existing = db.query(Category).filter(Category.slug == sub_in.slug.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Subcategory slug '{sub_in.slug}' already exists")

    sub = Category(
        parent_id=parent.id,
        name=sub_in.name,
        slug=sub_in.slug.lower().replace(" ", "-"),
        base_price_paise=sub_in.base_price_paise or parent.base_price_paise,
        active=sub_in.active,
        version=1
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    db.add(AuditLog(actor_id=current_user.id, action="SUBCATEGORY_CREATED", entity="category", entity_id=str(sub.id), meta={"parent_id": parent.id, "slug": sub.slug}))
    db.commit()

    return {"id": sub.id, "parent_id": sub.parent_id, "name": sub.name, "slug": sub.slug, "base_price_paise": sub.base_price_paise, "active": sub.active}

@router.patch("/taxonomy/subcategories/{subcategory_id}", response_model=Dict[str, Any])
def update_subcategory(
    subcategory_id: int,
    sub_in: AdminSubcategoryUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    sub = db.query(Category).filter(Category.id == subcategory_id).first()
    if not sub or not sub.parent_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subcategory not found")

    if sub_in.name is not None:
        sub.name = sub_in.name
    if sub_in.slug is not None:
        sub.slug = sub_in.slug.lower().replace(" ", "-")
    if sub_in.base_price_paise is not None:
        sub.base_price_paise = sub_in.base_price_paise
    if sub_in.active is not None:
        sub.active = sub_in.active

    sub.version += 1
    db.add(AuditLog(actor_id=current_user.id, action="SUBCATEGORY_UPDATED", entity="category", entity_id=str(sub.id)))
    db.commit()
    db.refresh(sub)

    return {"id": sub.id, "parent_id": sub.parent_id, "name": sub.name, "slug": sub.slug, "base_price_paise": sub.base_price_paise, "active": sub.active, "version": sub.version}

# ==========================================
# 3. PLATFORM ANALYTICS & AUDIT LOGS
# ==========================================

@router.get("/analytics", response_model=PlatformAnalyticsOut)
def get_platform_analytics(
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    # 1. Gross Marketplace Volume (Paid Orders)
    gmv_paise = db.query(func.sum(Order.amount_paise)).filter(Order.status == OrderStatus.PAID).scalar() or 0

    # 2. Platform 20% Fee Revenue
    platform_revenue = (
        db.query(func.sum(LedgerEntry.amount_paise))
        .filter(
            LedgerEntry.account_type == AccountType.PLATFORM,
            LedgerEntry.kind == EntryKind.PLATFORM_FEE,
            LedgerEntry.direction == EntryDirection.CREDIT
        )
        .scalar() or 0
    )

    # 3. Contributor Payouts
    payouts_total = (
        db.query(func.sum(PayoutRequest.amount_paise))
        .filter(PayoutRequest.status == PayoutStatus.COMPLETED)
        .scalar() or 0
    )

    # 4. User counts
    contributors_count = db.query(User).filter(User.role == UserRole.CONTRIBUTOR).count()
    agencies_count = db.query(User).filter(User.role == UserRole.AGENCY).count()

    # 5. Dataset / Listing counts
    total_uploads = db.query(Upload).count()
    active_listings = db.query(Listing).filter(Listing.status == ListingStatus.ACTIVE).count()
    orders_paid_count = db.query(Order).filter(Order.status == OrderStatus.PAID).count()
    licenses_count = db.query(License).count()

    # 6. Category breakdown
    categories = db.query(Category).filter(Category.parent_id.is_(None), Category.active == True).all()
    cat_distribution = []
    for c in categories:
        uploads_count = db.query(Upload).filter(Upload.category_id == c.id).count()
        published_count = (
            db.query(Listing)
            .join(Upload, Listing.upload_id == Upload.id)
            .filter(Upload.category_id == c.id, Listing.status == ListingStatus.ACTIVE)
            .count()
        )
        cat_distribution.append({
            "category_id": c.id,
            "category_name": c.name,
            "category_slug": c.slug,
            "uploads_count": uploads_count,
            "published_count": published_count,
            "base_price_paise": c.base_price_paise
        })

    return PlatformAnalyticsOut(
        gmv_paise=gmv_paise,
        platform_revenue_paise=platform_revenue,
        contributor_payouts_paise=payouts_total,
        total_contributors=contributors_count,
        total_agencies=agencies_count,
        total_uploads=total_uploads,
        total_active_listings=active_listings,
        total_orders_paid=orders_paid_count,
        total_licenses_issued=licenses_count,
        category_distribution=cat_distribution
    )

@router.get("/audit-logs", response_model=AuditLogPagination)
def get_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    action: Optional[str] = None,
    entity: Optional[str] = None,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if entity:
        query = query.filter(AuditLog.entity == entity)

    total = query.count()
    offset = (page - 1) * limit
    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for log in logs:
        actor_email = None
        if log.actor_id:
            actor = db.query(User).filter(User.id == log.actor_id).first()
            if actor:
                actor_email = actor.email

        items.append(
            AuditLogOut(
                id=log.id,
                actor_id=log.actor_id,
                actor_email=actor_email,
                action=log.action,
                entity=log.entity,
                entity_id=log.entity_id,
                meta=log.meta,
                created_at=log.created_at
            )
        )

    return AuditLogPagination(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=math.ceil(total / limit) if total > 0 else 1
    )
