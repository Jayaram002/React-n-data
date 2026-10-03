from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.schemas.consent import ConsentReacceptIn
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.user import User, ContributorProfile, AgencyProfile, UserRole
from app.models.ledger import Wallet
from app.schemas.user import UserRegister, UserLogin, Token, TokenRefresh, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # ── DPDP Act 2025 Registration Consent Enforcement ───────────────────
    if user_in.is_adult_confirmed is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation that you are 18 years of age or older is mandatory under the DPDP Act 2023 / Rules 2025"
        )
    if user_in.terms_accepted is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must review and accept the Terms of Service"
        )
    if user_in.privacy_accepted is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must review and accept the Privacy Notice"
        )

    from app.services.consent.consent_service import ConsentService
    from app.models.consent import ConsentPurpose

    active_terms = ConsentService.get_active_document(db, ConsentPurpose.TERMS_OF_SERVICE.value)
    active_privacy = ConsentService.get_active_document(db, ConsentPurpose.PRIVACY_NOTICE.value)
    if not active_terms or not active_privacy:
        ConsentService.seed_default_documents(db)
        active_terms = ConsentService.get_active_document(db, ConsentPurpose.TERMS_OF_SERVICE.value)
        active_privacy = ConsentService.get_active_document(db, ConsentPurpose.PRIVACY_NOTICE.value)

    terms_ver = active_terms.version if active_terms else "1.0"
    privacy_ver = active_privacy.version if active_privacy else "1.0"

    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        role=user_in.role,
        terms_accepted_version=terms_ver,
        privacy_accepted_version=privacy_ver,
        is_adult_confirmed=True
    )
    db.add(user)
    db.flush()

    # Record append-only immutable consent records for both
    if active_terms:
        ConsentService.record_consent(
            db=db,
            user_id=user.id,
            purpose_code=ConsentPurpose.TERMS_OF_SERVICE.value,
            document_id=active_terms.id,
            document_sha256=active_terms.sha256,
            action="granted"
        )
    if active_privacy:
        ConsentService.record_consent(
            db=db,
            user_id=user.id,
            purpose_code=ConsentPurpose.PRIVACY_NOTICE.value,
            document_id=active_privacy.id,
            document_sha256=active_privacy.sha256,
            action="granted"
        )

    if user_in.role == UserRole.CONTRIBUTOR:
        display_name = user_in.display_name or user_in.email.split("@")[0]
        profile = ContributorProfile(user_id=user.id, display_name=display_name)
        db.add(profile)
        # Create wallet for contributor
        wallet = Wallet(user_id=user.id, pending_balance_paise=0, available_balance_paise=0)
        db.add(wallet)
    elif user_in.role == UserRole.AGENCY:
        company_name = user_in.company_name or f"{user_in.email.split('@')[0]} Agency"
        profile = AgencyProfile(user_id=user.id, company_name=company_name)
        db.add(profile)

    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_in.email).first()
    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended"
        )

    access_token = create_access_token(subject=user.id, role=user.role.value)
    refresh_token = create_refresh_token(subject=user.id, role=user.role.value)

    return Token(access_token=access_token, refresh_token=refresh_token)

@router.post("/refresh", response_model=Token)
def refresh_token(refresh_in: TokenRefresh, db: Session = Depends(get_db)):
    payload = decode_token(refresh_in.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active"
        )

    new_access_token = create_access_token(subject=user.id, role=user.role.value)
    new_refresh_token = create_refresh_token(subject=user.id, role=user.role.value)

    return Token(access_token=new_access_token, refresh_token=new_refresh_token)

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/reaccept-consent", response_model=UserOut)
def reaccept_consent(
    reaccept_in: ConsentReacceptIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.services.consent.consent_service import ConsentService
    from app.models.consent import ConsentPurpose

    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    if reaccept_in.terms_accepted:
        active_terms = ConsentService.get_active_document(db, ConsentPurpose.TERMS_OF_SERVICE.value)
        if active_terms:
            current_user.terms_accepted_version = active_terms.version
            ConsentService.record_consent(
                db=db,
                user_id=current_user.id,
                purpose_code=ConsentPurpose.TERMS_OF_SERVICE.value,
                document_id=active_terms.id,
                document_sha256=active_terms.sha256,
                action="granted",
                ip=ip,
                user_agent=user_agent
            )

    if reaccept_in.privacy_accepted:
        active_privacy = ConsentService.get_active_document(db, ConsentPurpose.PRIVACY_NOTICE.value)
        if active_privacy:
            current_user.privacy_accepted_version = active_privacy.version
            ConsentService.record_consent(
                db=db,
                user_id=current_user.id,
                purpose_code=ConsentPurpose.PRIVACY_NOTICE.value,
                document_id=active_privacy.id,
                document_sha256=active_privacy.sha256,
                action="granted",
                ip=ip,
                user_agent=user_agent
            )

    db.commit()
    db.refresh(current_user)
    return current_user

