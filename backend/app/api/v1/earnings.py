from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.ledger import ContributorEarningsSummary, WalletOut
from app.services.ledger.ledger_service import (
    get_contributor_earnings,
    release_matured_pending_balances,
    get_wallet_or_create
)

router = APIRouter(prefix="/earnings", tags=["earnings"])

@router.get("/me", response_model=ContributorEarningsSummary)
def get_my_earnings(
    current_user: User = Depends(require_roles([UserRole.CONTRIBUTOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    return get_contributor_earnings(db, current_user.id)

@router.get("/wallet", response_model=WalletOut)
def get_my_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    wallet = get_wallet_or_create(db, current_user.id)
    return WalletOut.model_validate(wallet)

@router.post("/release-pending", response_model=Dict[str, Any])
def release_pending_funds(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Release pending funds for current contributor (or all if admin)
    user_id = None if current_user.role == UserRole.ADMIN else current_user.id
    result = release_matured_pending_balances(db, user_id=user_id)
    return {
        "status": "success",
        "detail": f"Released {result['released_amount_paise'] / 100:.2f} to available balance",
        **result
    }
