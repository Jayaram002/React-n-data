from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.schemas.order import MockCheckoutOut, MockPaymentSimulate, OrderOut
from app.services.payment.payment_service import process_payment_webhook_event
from app.api.v1.listings import format_listing_item

router = APIRouter(prefix="/mock", tags=["mock-payments"])

@router.get("/orders/{order_id}/checkout", response_model=MockCheckoutOut)
def get_mock_checkout_details(
    order_id: int,
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    listing = order.listing
    upload = listing.upload if listing else None
    contributor_name = "Verified Contributor"
    if upload and upload.contributor and upload.contributor.contributor_profile:
        contributor_name = upload.contributor.contributor_profile.display_name

    return MockCheckoutOut(
        order_id=order.id,
        listing_id=order.listing_id,
        listing_title=upload.title if upload else "Dataset License",
        contributor_name=contributor_name,
        amount_paise=order.amount_paise,
        currency="INR / USD",
        status=order.status,
        provider_ref=f"mock_order_{order.id}",
        ai_training_allowed=upload.ai_training_allowed if upload else True
    )

@router.post("/orders/{order_id}/simulate", response_model=OrderOut)
def simulate_mock_payment(
    order_id: int,
    sim_in: MockPaymentSimulate,
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if sim_in.result not in ("paid", "failed", "cancelled"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid result. Must be paid, failed, or cancelled")

    # Delegate to idempotent webhook event processor
    updated_order = process_payment_webhook_event(
        db=db,
        order_id=order_id,
        event_status=sim_in.result,
        provider_ref=f"mock_txn_{order_id}",
        raw_payload={"source": "simulation_ui", "result": sim_in.result}
    )

    return OrderOut(
        id=updated_order.id,
        buyer_id=updated_order.buyer_id,
        listing_id=updated_order.listing_id,
        amount_paise=updated_order.amount_paise,
        status=updated_order.status,
        created_at=updated_order.created_at,
        listing=format_listing_item(updated_order.listing) if updated_order.listing else None,
        license=updated_order.license
    )
