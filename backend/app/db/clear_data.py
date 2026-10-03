import os
import shutil
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.db.init_db import init_db
from app.models.user import User, UserRole, UserStatus, ContributorProfile, AgencyProfile
from app.models.category import Category
from app.models.upload import Upload, UploadFile
from app.models.listing import Listing
from app.models.ai import AIAnalysis
from app.models.order import Order, License
from app.models.ledger import Wallet, LedgerEntry, PayoutRequest
from app.models.audit import Flag, AuditLog, DownloadLog

def clear_all_mock_data(db: Session) -> None:
    """
    Purges all mock and seeded datasets, orders, listings, payments, wallets, and non-admin test users.
    Leaves the database clean with only the essential base taxonomy tree and platform admin account.
    """
    print("[1/3] Removing all mock orders, licenses, downloads, and ledger entries...")
    db.query(DownloadLog).delete()
    db.query(License).delete()
    
    # Check if Payment model exists
    try:
        from app.models.order import Payment
        db.query(Payment).delete()
    except Exception:
        pass

    db.query(Order).delete()
    db.query(PayoutRequest).delete()
    db.query(LedgerEntry).delete()
    db.query(Wallet).delete()
    db.query(Flag).delete()
    db.query(AuditLog).delete()
    db.commit()

    print("[2/3] Removing all mock uploads, listings, AI analyses, and test profiles...")
    db.query(Listing).delete()
    db.query(AIAnalysis).delete()
    db.query(UploadFile).delete()
    db.query(Upload).delete()
    db.query(ContributorProfile).delete()
    db.query(AgencyProfile).delete()
    
    # Remove all non-admin users
    db.query(User).filter(User.role != UserRole.ADMIN).delete()
    db.commit()

    # Ensure admin user exists
    admin_user = db.query(User).filter(User.email == "admin@reactndata.com").first()
    if not admin_user:
        admin_user = User(
            email="admin@reactndata.com",
            password_hash=get_password_hash("Password123!"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE
        )
        db.add(admin_user)
        db.commit()

    print("[3/3] Clearing local storage uploads & preview cache...")
    storage_root = Path("./storage").resolve()
    uploads_dir = storage_root / "uploads"
    previews_dir = storage_root / "previews"

    if uploads_dir.exists():
        for item in uploads_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            elif item.is_file() and item.name != ".gitkeep":
                item.unlink(missing_ok=True)

    if previews_dir.exists():
        for item in previews_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            elif item.is_file() and item.name != ".gitkeep":
                item.unlink(missing_ok=True)

    # Re-initialize clean taxonomy if needed
    init_db(db)

    print("SUCCESS: All mock data removed! Database is clean with base taxonomy and Admin ready.")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        clear_all_mock_data(db)
    finally:
        db.close()
