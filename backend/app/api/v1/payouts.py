from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.ledger import PayoutRequest
from app.schemas.ledger import (
    PayoutRequestCreate, PayoutRequestOut, PayoutProcessIn
)
from app.services.ledger.ledger_service import (
    request_payout, process_payout_request
)

router = APIRouter(prefix="/payouts", tags=["payouts"])

@router.post("/request", response_model=PayoutRequestOut, status_code=status.HTTP_201_CREATED)
def create_payout_request(
    payout_in: PayoutRequestCreate,
    current_user: User = Depends(require_roles([UserRole.CONTRIBUTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    try:
        payout = request_payout(
            db=db,
            user_id=current_user.id,
            amount_paise=payout_in.amount_paise,
            method=payout_in.method,
            destination=payout_in.destination
        )
        return PayoutRequestOut.model_validate(payout)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/mine", response_model=List[PayoutRequestOut])
def get_my_payout_requests(
    current_user: User = Depends(require_roles([UserRole.CONTRIBUTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    payouts = (
        db.query(PayoutRequest)
        .filter(PayoutRequest.user_id == current_user.id)
        .order_by(PayoutRequest.created_at.desc())
        .all()
    )
    return [PayoutRequestOut.model_validate(p) for p in payouts]

@router.post("/{payout_id}/process", response_model=PayoutRequestOut)
def process_payout(
    payout_id: int,
    proc_in: PayoutProcessIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Admin or the contributor simulating their payout in sandbox
    payout = db.query(PayoutRequest).filter(PayoutRequest.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout request not found")

    if payout.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    try:
        updated = process_payout_request(
            db=db,
            payout_id=payout_id,
            action=proc_in.action,
            actor_id=current_user.id,
            reason=proc_in.reason
        )
        return PayoutRequestOut.model_validate(updated)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
