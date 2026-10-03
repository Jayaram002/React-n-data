from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class UploadStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    PUBLISHED = "published"
    REJECTED = "rejected"
    FLAGGED = "flagged"
    UNPUBLISHED = "unpublished"
    HELD_UNCATEGORIZED = "held_uncategorized"

class CategorySource(str, enum.Enum):
    AI = "ai"
    CONTRIBUTOR = "contributor"
    ADMIN = "admin"

class DataType(str, enum.Enum):
    IMAGE = "image"
    TABULAR = "tabular"

class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    contributor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(UploadStatus), default=UploadStatus.UPLOADED, nullable=False, index=True)
    
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    subcategory_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    category_source = Column(Enum(CategorySource), default=CategorySource.AI, nullable=False)
    category_confidence = Column(Float, nullable=True)
    tags = Column(JSON, default=list, nullable=False) # Store array of tags as JSON
    
    price_paise = Column(Integer, nullable=True)
    ai_min_price = Column(Integer, nullable=True)
    ai_max_price = Column(Integer, nullable=True)
    ai_training_allowed = Column(Boolean, default=True, nullable=False)
    
    consent_version = Column(String, nullable=False, default="1.0")
    consent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    contributor = relationship("User", foreign_keys=[contributor_id])
    category = relationship("Category", foreign_keys=[category_id])
    subcategory = relationship("Category", foreign_keys=[subcategory_id])
    file_info = relationship("UploadFile", back_populates="upload", uselist=False, cascade="all, delete-orphan")
    ai_analysis = relationship("AIAnalysis", back_populates="upload", uselist=False, cascade="all, delete-orphan")
    listing = relationship("Listing", back_populates="upload", uselist=False, cascade="all, delete-orphan")

class UploadFile(Base):
    __tablename__ = "upload_files"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id", ondelete="CASCADE"), unique=True, nullable=False)
    data_type = Column(Enum(DataType), nullable=False)
    storage_key = Column(String, nullable=False)
    preview_key = Column(String, nullable=True)
    mime = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    
    # Image properties
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    phash = Column(String, nullable=True, index=True)
    exif_stripped = Column(Boolean, default=False, nullable=False)
    
    # Tabular properties
    row_count = Column(Integer, nullable=True)
    column_schema = Column(JSON, nullable=True)
    content_hash = Column(String, nullable=True, index=True)
    signature_hash = Column(String, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    upload = relationship("Upload", back_populates="file_info")
