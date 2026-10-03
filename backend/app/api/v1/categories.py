from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.api.deps import get_db
from app.models.category import Category
from app.models.listing import Listing, ListingStatus
from app.models.upload import Upload
from app.schemas.category import CategoryTreeOut, SubcategoryOut
from app.schemas.listing import ListingPaginationEnvelope
from app.api.v1.listings import browse_listings

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("", response_model=List[CategoryTreeOut])
def list_categories(db: Session = Depends(get_db)):
    # Fetch root categories (parent_id is null)
    domains = db.query(Category).filter(Category.parent_id.is_(None), Category.active == True).all()
    
    # Calculate counts per category
    result = []
    for domain in domains:
        subs = db.query(Category).filter(Category.parent_id == domain.id, Category.active == True).all()
        sub_ids = [s.id for s in subs]
        
        # Domain level count: direct uploads or in any subcategory
        domain_count = (
            db.query(func.count(Listing.id))
            .join(Upload, Upload.id == Listing.upload_id)
            .filter(
                Listing.status == ListingStatus.ACTIVE,
                or_(Upload.category_id == domain.id, Upload.subcategory_id.in_(sub_ids))
            )
            .scalar()
        ) or 0

        sub_list = []
        for sub in subs:
            sub_count = (
                db.query(func.count(Listing.id))
                .join(Upload, Upload.id == Listing.upload_id)
                .filter(
                    Listing.status == ListingStatus.ACTIVE,
                    Upload.subcategory_id == sub.id
                )
                .scalar()
            ) or 0

            sub_list.append(
                SubcategoryOut(
                    id=sub.id,
                    parent_id=sub.parent_id,
                    slug=sub.slug,
                    name=sub.name,
                    base_price_paise=sub.base_price_paise,
                    active=sub.active,
                    version=sub.version,
                    published_count=sub_count
                )
            )
        
        result.append(
            CategoryTreeOut(
                id=domain.id,
                slug=domain.slug,
                name=domain.name,
                base_price_paise=domain.base_price_paise,
                active=domain.active,
                version=domain.version,
                published_count=domain_count,
                subcategories=sub_list
            )
        )
    return result

@router.get("/{slug}/listings", response_model=ListingPaginationEnvelope)
def get_category_listings(
    slug: str,
    subcategory: Optional[str] = Query(None),
    data_type: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
    max_score: Optional[float] = Query(None),
    min_price: Optional[int] = Query(None),
    max_price: Optional[int] = Query(None),
    sort: Optional[str] = Query("newest"),
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db)
):
    cat = db.query(Category).filter(Category.slug == slug).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Category '{slug}' not found")
    
    return browse_listings(
        category=slug,
        subcategory=subcategory,
        data_type=data_type,
        tag=tag,
        q=q,
        min_score=min_score,
        max_score=max_score,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        page=page,
        limit=limit,
        db=db
    )
