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

@router.post("", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
async def create_upload(
    title: str = Form(...),
    description: str = Form(...),
    ai_training_allowed: bool = Form(True),
    consent_agreed: bool = Form(...),
    consent_version: str = Form("1.0"),
    file: FastAPIBaseUploadFile = File(...),
    current_user: User = Depends(require_roles([UserRole.CONTRIBUTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    if not consent_agreed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must agree to the data ownership and consent declaration"
        )
    
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty"
        )

    try:
        upload = execute_upload_pipeline(
            db=db,
            contributor_id=current_user.id,
            title=title,
            description=description,
            ai_training_allowed=ai_training_allowed,
            consent_version=consent_version,
            filename=file.filename or "uploaded_data",
            file_bytes=file_bytes
        )
        
        # Run AI analysis on the dataset
        run_full_ai_analysis(db, upload.id)
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

    if upload.status not in (UploadStatus.ANALYZED, UploadStatus.UNPUBLISHED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish upload in status '{upload.status}'. Must be analyzed."
        )

    if not upload.category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish upload without an assigned category domain."
        )

    if not upload.price_paise:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish upload without a listing price."
        )

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
