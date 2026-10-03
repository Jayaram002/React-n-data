from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus, License
from app.models.listing import Listing, ListingStatus
from app.models.upload import Upload, UploadFile
from app.models.audit import DownloadLog
from app.schemas.order import OrderCreate, OrderOut
from app.api.v1.listings import format_listing_item
from app.services.payment import get_payment_provider
from app.services.storage import get_storage_service

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    order_in: OrderCreate,
    current_user: User = Depends(require_roles([UserRole.AGENCY, UserRole.CONTRIBUTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    listing = db.query(Listing).filter(Listing.id == order_in.listing_id).first()
    if not listing or listing.status != ListingStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active listing not found")

    upload = listing.upload
    if not upload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Listing upload record missing")

    # Prevent contributor from buying their own data
    if upload.contributor_id == current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot purchase your own listing")

    order = Order(
        buyer_id=current_user.id,
        listing_id=listing.id,
        amount_paise=upload.price_paise or 500000,
        status=OrderStatus.AWAITING_PAYMENT
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # Initialize payment order with provider
    payment_provider = get_payment_provider()
    payment_provider.create_order(order.id, order.amount_paise)

    return OrderOut(
        id=order.id,
        buyer_id=order.buyer_id,
        listing_id=order.listing_id,
        amount_paise=order.amount_paise,
        status=order.status,
        created_at=order.created_at,
        listing=format_listing_item(listing) if listing else None,
        license=None
    )

@router.get("/mine", response_model=List[OrderOut])
def get_my_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    orders = (
        db.query(Order)
        .filter(Order.buyer_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    result = []
    for order in orders:
        result.append(
            OrderOut(
                id=order.id,
                buyer_id=order.buyer_id,
                listing_id=order.listing_id,
                amount_paise=order.amount_paise,
                status=order.status,
                created_at=order.created_at,
                listing=format_listing_item(order.listing) if order.listing else None,
                license=order.license
            )
        )
    return result

@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.buyer_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    return OrderOut(
        id=order.id,
        buyer_id=order.buyer_id,
        listing_id=order.listing_id,
        amount_paise=order.amount_paise,
        status=order.status,
        created_at=order.created_at,
        listing=format_listing_item(order.listing) if order.listing else None,
        license=order.license
    )

@router.get("/{order_id}/download")
def download_licensed_dataset(
    order_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Only the paid buyer or Admin can download
    if order.buyer_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    if order.status != OrderStatus.PAID:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dataset download requires a completed paid order")

    upload = order.listing.upload if order.listing else None
    if not upload or not upload.file_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original dataset file not found")

    file_info = upload.file_info
    storage_service = get_storage_service()

    try:
        file_bytes = storage_service.get_file(file_info.storage_key)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original file missing from storage")

    # Log download in audit
    client_ip = request.client.host if request.client else "unknown"
    license_id = order.license.id if order.license else 0
    download_log = DownloadLog(
        license_id=license_id,
        user_id=current_user.id,
        ip=client_ip
    )
    db.add(download_log)
    db.commit()

    # Determine attachment filename
    ext = file_info.storage_key.split(".")[-1] if "." in file_info.storage_key else "bin"
    filename = f"dataset_{upload.id}_{upload.title.lower().replace(' ', '_')}.{ext}"

    return Response(
        content=file_bytes,
        media_type=file_info.mime,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
