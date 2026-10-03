import json
import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from app.api.deps import get_db, get_current_user
from app.models.listing import Listing, ListingStatus
from app.models.upload import Upload, UploadFile, DataType
from app.models.category import Category
from app.models.ai import AIAnalysis
from app.models.user import User, ContributorProfile
from app.schemas.listing import ListingItemOut, ListingDetailOut, ListingPaginationEnvelope, ListingCategoryOut, ListingContributorOut
from app.schemas.ai import AIAnalysisOut
from app.services.storage import get_storage_service

router = APIRouter(prefix="/listings", tags=["listings"])

def format_listing_item(listing: Listing) -> ListingItemOut:
    upload = listing.upload
    file_info = upload.file_info if upload else None
    ai_analysis = upload.ai_analysis if upload else None

    # Resolve contributor info
    contributor = None
    if upload and upload.contributor:
        prof = upload.contributor.contributor_profile
        contributor = ListingContributorOut(
            id=upload.contributor.id,
            display_name=prof.display_name if prof else "Verified Contributor",
            reputation_score=prof.reputation_score if prof else 80.0
        )

    # Resolve categories
    category_out = None
    if upload and upload.category:
        category_out = ListingCategoryOut(
            id=upload.category.id,
            slug=upload.category.slug,
            name=upload.category.name,
            base_price_paise=upload.category.base_price_paise
        )

    subcategory_out = None
    if upload and upload.subcategory:
        subcategory_out = ListingCategoryOut(
            id=upload.subcategory.id,
            slug=upload.subcategory.slug,
            name=upload.subcategory.name,
            base_price_paise=upload.subcategory.base_price_paise
        )

    return ListingItemOut(
        id=listing.id,
        upload_id=upload.id,
        title=upload.title,
        description=upload.description,
        status=listing.status,
        data_type=file_info.data_type if file_info else DataType.TABULAR,
        price_paise=upload.price_paise or 500000,
        trust_score=ai_analysis.total_score if ai_analysis else 80.0,
        category=category_out,
        subcategory=subcategory_out,
        tags=upload.tags or [],
        contributor=contributor,
        ai_training_allowed=upload.ai_training_allowed,
        size=file_info.size if file_info else 0,
        published_at=listing.published_at,
        created_at=listing.created_at
    )

@router.get("/browse", response_model=ListingPaginationEnvelope)
def browse_listings(
    category: Optional[str] = Query(None, description="Domain category slug"),
    subcategory: Optional[str] = Query(None, description="Subcategory slug"),
    data_type: Optional[DataType] = Query(None, description="image or tabular"),
    tag: Optional[str] = Query(None, description="Keyword tag search"),
    q: Optional[str] = Query(None, description="Search keyword in title/description"),
    min_score: Optional[float] = Query(None, description="Minimum Trust Score (0-100)"),
    max_score: Optional[float] = Query(None, description="Maximum Trust Score (0-100)"),
    min_price: Optional[int] = Query(None, description="Minimum price in paise"),
    max_price: Optional[int] = Query(None, description="Maximum price in paise"),
    sort: Optional[str] = Query("newest", description="newest, score_desc, price_asc, price_desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db)
):
    query = (
        db.query(Listing)
        .join(Upload, Upload.id == Listing.upload_id)
        .outerjoin(UploadFile, UploadFile.upload_id == Upload.id)
        .outerjoin(AIAnalysis, AIAnalysis.upload_id == Upload.id)
        .filter(Listing.status == ListingStatus.ACTIVE)
    )

    # Category filters
    if category:
        cat_obj = db.query(Category).filter(Category.slug == category).first()
        if cat_obj:
            if cat_obj.parent_id is None:
                # Root domain: match category_id directly OR subcategories of this domain
                sub_ids = [s.id for s in db.query(Category.id).filter(Category.parent_id == cat_obj.id).all()]
                query = query.filter(or_(Upload.category_id == cat_obj.id, Upload.subcategory_id.in_(sub_ids)))
            else:
                query = query.filter(or_(Upload.category_id == cat_obj.id, Upload.subcategory_id == cat_obj.id))

    if subcategory:
        sub_obj = db.query(Category).filter(Category.slug == subcategory).first()
        if sub_obj:
            query = query.filter(Upload.subcategory_id == sub_obj.id)

    if data_type:
        query = query.filter(UploadFile.data_type == data_type)

    if q:
        search_pattern = f"%{q}%"
        query = query.filter(or_(Upload.title.ilike(search_pattern), Upload.description.ilike(search_pattern)))

    if min_score is not None:
        query = query.filter(AIAnalysis.total_score >= min_score)
    if max_score is not None:
        query = query.filter(AIAnalysis.total_score <= max_score)

    if min_price is not None:
        query = query.filter(Upload.price_paise >= min_price)
    if max_price is not None:
        query = query.filter(Upload.price_paise <= max_price)

    # Sorting
    if sort == "score_desc":
        query = query.order_by(desc(AIAnalysis.total_score))
    elif sort == "price_asc":
        query = query.order_by(asc(Upload.price_paise))
    elif sort == "price_desc":
        query = query.order_by(desc(Upload.price_paise))
    else: # newest
        query = query.order_by(desc(Listing.published_at))

    total = query.count()
    total_pages = math.ceil(total / limit) if total > 0 else 1
    offset = (page - 1) * limit
    listings = query.offset(offset).limit(limit).all()

    items = [format_listing_item(l) for l in listings]

    return ListingPaginationEnvelope(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@router.get("/{listing_id}", response_model=ListingDetailOut)
def get_listing_detail(
    listing_id: int,
    db: Session = Depends(get_db)
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    upload = listing.upload
    file_info = upload.file_info if upload else None
    ai_analysis = upload.ai_analysis if upload else None

    contributor = None
    if upload and upload.contributor:
        prof = upload.contributor.contributor_profile
        contributor = ListingContributorOut(
            id=upload.contributor.id,
            display_name=prof.display_name if prof else "Verified Contributor",
            reputation_score=prof.reputation_score if prof else 80.0
        )

    category_out = None
    if upload and upload.category:
        category_out = ListingCategoryOut(
            id=upload.category.id,
            slug=upload.category.slug,
            name=upload.category.name,
            base_price_paise=upload.category.base_price_paise
        )

    subcategory_out = None
    if upload and upload.subcategory:
        subcategory_out = ListingCategoryOut(
            id=upload.subcategory.id,
            slug=upload.subcategory.slug,
            name=upload.subcategory.name,
            base_price_paise=upload.subcategory.base_price_paise
        )

    analysis_out = None
    if ai_analysis:
        analysis_out = AIAnalysisOut(
            id=ai_analysis.id,
            upload_id=ai_analysis.upload_id,
            model_name=ai_analysis.model_name,
            config_version=ai_analysis.config_version,
            taxonomy_version=ai_analysis.taxonomy_version,
            classification_output=ai_analysis.classification_output,
            quality=ai_analysis.quality,
            authenticity=ai_analysis.authenticity,
            uniqueness=ai_analysis.uniqueness,
            metadata_accuracy=ai_analysis.metadata_accuracy,
            reputation=ai_analysis.reputation,
            total_score=ai_analysis.total_score,
            explanation=ai_analysis.explanation,
            tips=ai_analysis.tips,
            degraded=ai_analysis.degraded,
            ai_min_price=upload.ai_min_price,
            ai_max_price=upload.ai_max_price,
            suggested_price=upload.price_paise
        )

    file_metadata = {}
    if file_info:
        file_metadata = {
            "mime": file_info.mime,
            "size": file_info.size,
            "width": file_info.width,
            "height": file_info.height,
            "row_count": file_info.row_count,
            "column_schema": file_info.column_schema,
            "exif_stripped": file_info.exif_stripped
        }

    return ListingDetailOut(
        id=listing.id,
        upload_id=upload.id,
        title=upload.title,
        description=upload.description,
        status=listing.status,
        data_type=file_info.data_type if file_info else DataType.TABULAR,
        price_paise=upload.price_paise or 500000,
        ai_min_price=upload.ai_min_price,
        ai_max_price=upload.ai_max_price,
        category=category_out,
        subcategory=subcategory_out,
        tags=upload.tags or [],
        contributor=contributor,
        ai_training_allowed=upload.ai_training_allowed,
        ai_analysis=analysis_out,
        file_metadata=file_metadata,
        published_at=listing.published_at,
        created_at=listing.created_at
    )

@router.get("/{listing_id}/preview")
def get_listing_preview(
    listing_id: int,
    db: Session = Depends(get_db)
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing or listing.status != ListingStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing preview not found or not active")

    upload = listing.upload
    if not upload or not upload.file_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview unavailable")

    storage_service = get_storage_service()
    if upload.file_info.preview_key:
        try:
            preview_bytes = storage_service.get_file(upload.file_info.preview_key)
            if upload.file_info.data_type == DataType.IMAGE:
                return Response(content=preview_bytes, media_type="image/png")
            else:
                return JSONResponse(content=json.loads(preview_bytes.decode("utf-8")))
        except Exception:
            pass

    if upload.file_info.data_type == DataType.TABULAR:
        try:
            raw_bytes = storage_service.get_file(upload.file_info.storage_key)
            import io
            import pandas as pd
            df = pd.read_csv(io.BytesIO(raw_bytes))
            sample = df.head(5)
            cols = [{"name": c, "type": str(df[c].dtype)} for c in df.columns]
            return JSONResponse(content={
                "columns": cols,
                "sample_rows": sample.to_dict(orient="records"),
                "total_rows": len(df)
            })
        except Exception:
            cols = (upload.file_info.column_schema or {}).get("columns", [])
            return JSONResponse(content={
                "columns": cols,
                "sample_rows": [],
                "total_rows": upload.file_info.row_count or 0
            })

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview unavailable")
