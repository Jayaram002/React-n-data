import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile as FastAPIBaseUploadFile, Form, File, Response, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.upload import Upload, UploadFile, UploadStatus, DataType, CategorySource
from app.models.category import Category
from app.models.ai import AIAnalysis
from app.models.audit import Flag, FlagStatus
from app.schemas.upload import UploadOut, UploadListItemOut, PriceUpdate, CategoryUpdate
from app.schemas.ai import AIAnalysisOut
from app.services.prechecks.orchestrator import execute_upload_pipeline
from app.services.ai.ai_orchestrator import run_full_ai_analysis
from app.services.storage import get_storage_service

router = APIRouter(prefix="/uploads", tags=["uploads"])

import uuid
from fastapi import Request
from app.models.consent import ConsentPurpose
from app.schemas.consent import ConsentWithdrawRequest
from app.services.consent.consent_service import ConsentService

@router.post("", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
async def create_upload(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    contributor_rights_agreed: bool = Form(False),
    platform_license_agreed: bool = Form(False),
    personal_data_attestation_agreed: bool = Form(False),
    personal_data_status: str = Form("none"),
    lawful_basis: Optional[str] = Form(None),
    lawful_basis_note: Optional[str] = Form(None),
    ai_training_agreed: bool = Form(False),
    consent_agreed: Optional[bool] = Form(None),
    consent_version: str = Form("1.0"),
    file: FastAPIBaseUploadFile = File(...),
    evidence_file: Optional[FastAPIBaseUploadFile] = File(None),
    current_user: User = Depends(require_roles([UserRole.CONTRIBUTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    # Backward compatibility with legacy single checkbox
    if consent_agreed is True:
        contributor_rights_agreed = True
        platform_license_agreed = True
        personal_data_attestation_agreed = True

    # Validate purpose-specific required consents under DPDP Act / Rules 2025
    if not contributor_rights_agreed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must agree to the data ownership, consent declaration, and licensing terms"
        )
    if not platform_license_agreed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must grant the platform license to preview, host and license the dataset"
        )
    if not personal_data_attestation_agreed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must complete the personal data attestation"
        )

    if personal_data_status == "contains_personal_data":
        if not lawful_basis or not lawful_basis.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid lawful basis is required when dataset contains personal data"
            )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty"
        )

    # Save evidence file if provided (admin-only private evidence)
    evidence_key = None
    storage_service = get_storage_service()
    if evidence_file and evidence_file.filename:
        evidence_bytes = await evidence_file.read()
        if evidence_bytes:
            ext = "." + evidence_file.filename.rsplit(".", 1)[-1].lower() if "." in evidence_file.filename else ".bin"
            evidence_key = f"evidence/{uuid.uuid4().hex}{ext}"
            storage_service.save_file(evidence_bytes, evidence_key)

    ai_training_allowed = bool(ai_training_agreed)

    try:
        upload = execute_upload_pipeline(
            db=db,
            contributor_id=current_user.id,
            title=title,
            description=description,
            ai_training_allowed=ai_training_allowed,
            consent_version=consent_version,
            filename=file.filename or "uploaded_data",
            file_bytes=file_bytes,
            personal_data_status=personal_data_status,
            lawful_basis=lawful_basis,
            lawful_basis_note=lawful_basis_note,
            evidence_storage_key=evidence_key
        )

        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Record required consent records
        doc1 = ConsentService.get_active_document(db, ConsentPurpose.CONTRIBUTOR_RIGHTS_WARRANTY.value)
        doc2 = ConsentService.get_active_document(db, ConsentPurpose.PLATFORM_LISTING_LICENSE.value)
        doc3 = ConsentService.get_active_document(db, ConsentPurpose.THIRD_PARTY_DATA_ATTESTATION.value)
        if not doc1 or not doc2 or not doc3:
            ConsentService.seed_default_documents(db)
            doc1 = ConsentService.get_active_document(db, ConsentPurpose.CONTRIBUTOR_RIGHTS_WARRANTY.value)
            doc2 = ConsentService.get_active_document(db, ConsentPurpose.PLATFORM_LISTING_LICENSE.value)
            doc3 = ConsentService.get_active_document(db, ConsentPurpose.THIRD_PARTY_DATA_ATTESTATION.value)

        if doc1:
            ConsentService.record_consent(db, user_id=current_user.id, upload_id=upload.id, purpose_code=doc1.purpose_code, document_id=doc1.id, document_sha256=doc1.sha256, action="granted", ip=ip, user_agent=user_agent)
        if doc2:
            ConsentService.record_consent(db, user_id=current_user.id, upload_id=upload.id, purpose_code=doc2.purpose_code, document_id=doc2.id, document_sha256=doc2.sha256, action="granted", ip=ip, user_agent=user_agent)
        if doc3:
            ConsentService.record_consent(db, user_id=current_user.id, upload_id=upload.id, purpose_code=doc3.purpose_code, document_id=doc3.id, document_sha256=doc3.sha256, action="granted", ip=ip, user_agent=user_agent)

        if ai_training_allowed:
            doc4 = ConsentService.get_active_document(db, ConsentPurpose.AI_TRAINING_USE.value)
            if doc4:
                ConsentService.record_consent(db, user_id=current_user.id, upload_id=upload.id, purpose_code=doc4.purpose_code, document_id=doc4.id, document_sha256=doc4.sha256, action="granted", ip=ip, user_agent=user_agent)

        # Run AI analysis on the dataset
        run_full_ai_analysis(db, upload.id)
        db.commit()
        db.refresh(upload)
        return upload
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing upload: {str(exc)}"
        )

@router.post("/{upload_id}/consent/withdraw")
def withdraw_consent(
    upload_id: int,
    payload: ConsentWithdrawRequest,
    request: Request,
    current_user: User = Depends(require_roles([UserRole.CONTRIBUTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    if upload.contributor_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    rec, effects = ConsentService.withdraw_consent(
        db=db,
        user_id=current_user.id,
        purpose_code=payload.purpose_code,
        upload_id=upload_id,
        ip=ip,
        user_agent=user_agent
    )
    return {
        "status": "withdrawn",
        "purpose_code": payload.purpose_code,
        "record_id": rec.id,
        "effects": effects
    }

@router.get("/mine", response_model=List[UploadOut])
def get_my_uploads(
    current_user: User = Depends(require_roles([UserRole.CONTRIBUTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    uploads = (
        db.query(Upload)
        .filter(Upload.contributor_id == current_user.id)
        .order_by(Upload.created_at.desc())
        .all()
    )
    return uploads

@router.get("/{upload_id}", response_model=UploadOut)
def get_upload_details(
    upload_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    
    if upload.contributor_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")
    
    return upload

@router.get("/{upload_id}/analysis", response_model=AIAnalysisOut)
def get_upload_analysis(
    upload_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    
    if upload.contributor_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    analysis = db.query(AIAnalysis).filter(AIAnalysis.upload_id == upload_id).first()
    if not analysis:
        # If not analyzed yet, run it
        analysis = run_full_ai_analysis(db, upload_id)

    return AIAnalysisOut(
        id=analysis.id,
        upload_id=analysis.upload_id,
        model_name=analysis.model_name,
        config_version=analysis.config_version,
        taxonomy_version=analysis.taxonomy_version,
        classification_output=analysis.classification_output,
        quality=analysis.quality,
        authenticity=analysis.authenticity,
        uniqueness=analysis.uniqueness,
        metadata_accuracy=analysis.metadata_accuracy,
        reputation=analysis.reputation,
        total_score=analysis.total_score,
        explanation=analysis.explanation,
        tips=analysis.tips,
        degraded=analysis.degraded,
        ai_min_price=upload.ai_min_price,
        ai_max_price=upload.ai_max_price,
        suggested_price=upload.price_paise
    )

@router.post("/{upload_id}/analyze", response_model=AIAnalysisOut)
def trigger_analysis(
    upload_id: int,
    current_user: User = Depends(require_roles([UserRole.CONTRIBUTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    
    if upload.contributor_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    analysis = run_full_ai_analysis(db, upload_id)
    return analysis

@router.patch("/{upload_id}/price", response_model=UploadOut)
def update_price(
    upload_id: int,
    price_in: PriceUpdate,
    current_user: User = Depends(require_roles([UserRole.CONTRIBUTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    
    if upload.contributor_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    # Enforce price must be within AI min-max range
    if upload.ai_min_price and upload.ai_max_price:
        if price_in.price_paise < upload.ai_min_price or price_in.price_paise > upload.ai_max_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Price must be within the AI suggested range: {upload.ai_min_price/100:.2f} - {upload.ai_max_price/100:.2f}"
            )

    upload.price_paise = price_in.price_paise
    db.commit()
    db.refresh(upload)
    return upload

@router.patch("/{upload_id}/category", response_model=UploadOut)
def request_category_change(
    upload_id: int,
    cat_in: CategoryUpdate,
    current_user: User = Depends(require_roles([UserRole.CONTRIBUTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    
    if upload.contributor_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    category = db.query(Category).filter(Category.id == cat_in.category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category ID")

    # If contributor overrides a high-confidence Gemma pick, flag for admin review
    if upload.category_confidence and upload.category_confidence >= 0.75:
        flag = Flag(
            upload_id=upload.id,
            reason=f"Contributor requested category change to '{category.name}' overriding AI confidence ({upload.category_confidence:.2f})",
            source="contributor",
            status=FlagStatus.OPEN
        )
        db.add(flag)

    upload.category_id = cat_in.category_id
    upload.subcategory_id = cat_in.subcategory_id
    upload.category_source = CategorySource.CONTRIBUTOR
    if upload.status == UploadStatus.HELD_UNCATEGORIZED:
        upload.status = UploadStatus.ANALYZED

    db.commit()
    db.refresh(upload)
    return upload

@router.post("/{upload_id}/publish", response_model=UploadOut)
def publish_upload(
    upload_id: int,
    current_user: User = Depends(require_roles([UserRole.CONTRIBUTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    from app.models.listing import Listing, ListingStatus
    from datetime import datetime, timezone

    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    
    if upload.contributor_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    if upload.status == UploadStatus.FLAGGED:
        open_flags = [f.reason for f in upload.flags if f.status == FlagStatus.OPEN]
        flag_details = f" ({'; '.join(open_flags)})" if open_flags else ""
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish dataset while flagged for moderation review{flag_details}. Please resolve open flags before publishing."
        )

    if upload.status == UploadStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish a rejected dataset."
        )

    if not upload.category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please select an assigned Category domain for this dataset before publishing."
        )

    if not upload.price_paise or upload.price_paise <= 0:
        if upload.ai_min_price and upload.ai_min_price > 0:
            upload.price_paise = upload.ai_min_price
        else:
            upload.price_paise = 500000

    upload.status = UploadStatus.PUBLISHED
    
    # Create or activate listing
    listing = db.query(Listing).filter(Listing.upload_id == upload_id).first()
    if listing:
        listing.status = ListingStatus.ACTIVE
        listing.published_at = datetime.now(timezone.utc)
    else:
        listing = Listing(
            upload_id=upload.id,
            status=ListingStatus.ACTIVE,
            published_at=datetime.now(timezone.utc)
        )
        db.add(listing)

    db.commit()
    db.refresh(upload)
    return upload

@router.post("/{upload_id}/unpublish", response_model=UploadOut)
def unpublish_upload(
    upload_id: int,
    current_user: User = Depends(require_roles([UserRole.CONTRIBUTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    from app.models.listing import Listing, ListingStatus

    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    
    if upload.contributor_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    upload.status = UploadStatus.UNPUBLISHED
    
    listing = db.query(Listing).filter(Listing.upload_id == upload_id).first()
    if listing:
        listing.status = ListingStatus.INACTIVE

    db.commit()
    db.refresh(upload)
    return upload

@router.get("/{upload_id}/preview")
def get_upload_preview(
    upload_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    
    if not upload.file_info or not upload.file_info.preview_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview not available")

    storage_service = get_storage_service()
    try:
        preview_bytes = storage_service.get_file(upload.file_info.preview_key)
        if upload.file_info.data_type == DataType.IMAGE:
            return Response(content=preview_bytes, media_type="image/jpeg")
        else:
            return JSONResponse(content=json.loads(preview_bytes.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview file not found")
