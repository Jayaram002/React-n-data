from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id", ondelete="CASCADE"), unique=True, nullable=False)
    model_name = Column(String, nullable=False, default="gemma:2b")
    config_version = Column(String, nullable=False, default="1.0")
    taxonomy_version = Column(Integer, nullable=False, default=1)
    
    classification_output = Column(JSON, nullable=False)
    quality = Column(Float, nullable=False, default=0.0)
    authenticity = Column(Float, nullable=False, default=0.0)
    uniqueness = Column(Float, nullable=False, default=0.0)
    metadata_accuracy = Column(Float, nullable=False, default=0.0)
    reputation = Column(Float, nullable=False, default=0.0)
    total_score = Column(Float, nullable=False, default=0.0)
    
    explanation = Column(Text, nullable=False)
    tips = Column(JSON, nullable=False) # list of string tips
    degraded = Column(Boolean, default=False, nullable=False)
    raw_output = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    upload = relationship("Upload", back_populates="ai_analysis")
