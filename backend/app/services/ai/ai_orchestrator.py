import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.upload import Upload, UploadFile, UploadStatus, CategorySource, DataType
from app.models.category import Category
from app.models.ai import AIAnalysis
from app.models.user import ContributorProfile
from app.models.audit import Flag, FlagStatus
from app.core.config import settings
from app.core.ai_config import (
    TRUST_SCORE_WEIGHTS, AI_CONFIG_VERSION,
    CONFIDENCE_AUTO_ASSIGN_THRESHOLD, CONFIDENCE_REVIEW_THRESHOLD
)
from app.services.ai.gemini_service import GeminiAIService
from app.services.ai.embedding_service import EmbeddingService
from app.services.pricing.pricing_engine import calculate_suggested_price, get_demand_factor

def run_full_ai_analysis(db: Session, upload_id: int) -> AIAnalysis:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload or not upload.file_info:
        raise ValueError(f"Upload #{upload_id} or associated file not found")

    file_info = upload.file_info
    ai_service = GeminiAIService()
    embedding_service = EmbeddingService()

    # 1. Fetch Taxonomy for allowed category list
    categories = db.query(Category).filter(Category.active == True).all()
    allowed_categories = []
    cat_by_slug: Dict[str, Category] = {}
    for cat in categories:
        cat_by_slug[cat.slug] = cat
        if cat.parent_id is None:
            subs = [s for s in categories if s.parent_id == cat.id]
            allowed_categories.append({
                "slug": cat.slug,
                "name": cat.name,
                "subcategories": [{"slug": s.slug, "name": s.name} for s in subs]
            })

    # 2. Extract safe sample preview metadata (PII masked)
    sample_preview = None
    if file_info.data_type == DataType.TABULAR and file_info.column_schema:
        sample_preview = {
            "columns": file_info.column_schema.get("columns", []),
            "row_count": file_info.row_count
        }

    # 3. Classify Upload
    classification_out, class_degraded = ai_service.classify_upload(
        title=upload.title,
        description=upload.description,
        data_type=file_info.data_type.value,
        allowed_categories=allowed_categories,
        sample_preview=sample_preview
    )

    # 4. Resolve Domain & Subcategory Records
    primary_cat = cat_by_slug.get(classification_out.primary_category)
    sub_cat = cat_by_slug.get(classification_out.subcategory) if classification_out.subcategory else None

    # Determine Base Price (Inherited if subcategory has none)
    base_price_paise = 500000
    if sub_cat and sub_cat.base_price_paise:
        base_price_paise = sub_cat.base_price_paise
    elif primary_cat and primary_cat.base_price_paise:
        base_price_paise = primary_cat.base_price_paise

    # 5. Compute Uniqueness Score
    if file_info.data_type == DataType.IMAGE:
        uniqueness = embedding_service.calculate_image_uniqueness(db, file_info.phash, upload_id=upload.id)
    else:
        col_names = [c["name"] for c in (file_info.column_schema or {}).get("columns", [])]
        uniqueness = embedding_service.calculate_tabular_uniqueness(
            db, col_names, file_info.signature_hash or "", upload_id=upload.id
        )

    # 6. Compute Contributor Reputation (neutral default 80.0 for new users)
    contributor_profile = db.query(ContributorProfile).filter(ContributorProfile.user_id == upload.contributor_id).first()
    reputation = contributor_profile.reputation_score if contributor_profile else 80.0

    # 7. Quality, Authenticity & Metadata Accuracy Scoring
    precheck_metrics = {
        "width": file_info.width,
        "height": file_info.height,
        "size": file_info.size,
        "exif_stripped": file_info.exif_stripped,
        "row_count": file_info.row_count,
        "column_schema": file_info.column_schema,
        "content_hash": file_info.content_hash
    }

    scoring_out, score_degraded = ai_service.score_upload(
        title=upload.title,
        description=upload.description,
        data_type=file_info.data_type.value,
        category_slug=classification_out.primary_category,
        precheck_metrics=precheck_metrics,
        sample_preview=sample_preview
    )

    is_degraded = class_degraded or score_degraded

    # 8. Compute Hybrid Trust Score (Weighted Sum 0-100)
    total_score = (
        (scoring_out.quality * TRUST_SCORE_WEIGHTS["quality"]) +
        (scoring_out.authenticity * TRUST_SCORE_WEIGHTS["authenticity"]) +
        (uniqueness * TRUST_SCORE_WEIGHTS["uniqueness"]) +
        (scoring_out.metadata_accuracy * TRUST_SCORE_WEIGHTS["metadata_accuracy"]) +
        (reputation * TRUST_SCORE_WEIGHTS["reputation"])
    )
    total_score = round(min(100.0, max(0.0, total_score)), 1)

    # 9. Compute Pricing Suggestion & Min-Max Range
    demand_factor = get_demand_factor(classification_out.primary_category)
    pricing = calculate_suggested_price(base_price_paise, total_score, demand_factor)

    # 10. Apply Confidence Rules & Status Transitions
    confidence = classification_out.confidence
    if confidence >= CONFIDENCE_AUTO_ASSIGN_THRESHOLD:
        upload.category_id = primary_cat.id if primary_cat else None
        upload.subcategory_id = sub_cat.id if sub_cat else None
        if upload.status not in (UploadStatus.FLAGGED, UploadStatus.REJECTED):
            upload.status = UploadStatus.ANALYZED
    elif confidence >= CONFIDENCE_REVIEW_THRESHOLD:
        upload.category_id = primary_cat.id if primary_cat else None
        upload.subcategory_id = sub_cat.id if sub_cat else None
        if upload.status not in (UploadStatus.FLAGGED, UploadStatus.REJECTED):
            upload.status = UploadStatus.ANALYZED
        # Raise category review flag
        flag = Flag(
            upload_id=upload.id,
            reason=f"Category classification confidence ({confidence:.2f}) requires review",
            source="system",
            status=FlagStatus.OPEN
        )
        db.add(flag)
    else:
        # Confidence < 0.50 -> Hold uncategorized
        upload.category_id = None
        upload.subcategory_id = None
        if upload.status not in (UploadStatus.FLAGGED, UploadStatus.REJECTED):
            upload.status = UploadStatus.HELD_UNCATEGORIZED

    # DPDP Framework: Health and Finance domains require mandatory admin moderation
    primary_slug = (classification_out.primary_category or "").lower()
    if any(k in primary_slug for k in ["health", "finance", "medical", "banking"]):
        upload.status = UploadStatus.FLAGGED
        flag = Flag(
            upload_id=upload.id,
            reason=f"Upload routed to sensitive domain '{classification_out.primary_category}'. DPDP compliance requires admin moderation before listing.",
            source="system",
            status=FlagStatus.OPEN
        )
        db.add(flag)

    # Update Upload fields
    upload.category_confidence = confidence
    upload.tags = classification_out.tags
    upload.price_paise = pricing["suggested_price_paise"]
    upload.ai_min_price = pricing["ai_min_price_paise"]
    upload.ai_max_price = pricing["ai_max_price_paise"]

    # 11. Create or Update AIAnalysis Record
    existing_analysis = db.query(AIAnalysis).filter(AIAnalysis.upload_id == upload.id).first()
    if existing_analysis:
        analysis = existing_analysis
    else:
        analysis = AIAnalysis(upload_id=upload.id)
        db.add(analysis)

    analysis.model_name = settings.GEMINI_MODEL if settings.AI_PROVIDER == "gemini" else "mock-scorer"
    analysis.config_version = AI_CONFIG_VERSION
    analysis.taxonomy_version = primary_cat.version if primary_cat else 1
    analysis.classification_output = classification_out.model_dump()
    analysis.quality = scoring_out.quality
    analysis.authenticity = scoring_out.authenticity
    analysis.uniqueness = uniqueness
    analysis.metadata_accuracy = scoring_out.metadata_accuracy
    analysis.reputation = reputation
    analysis.total_score = total_score
    analysis.explanation = scoring_out.explanation
    analysis.tips = scoring_out.tips
    analysis.degraded = is_degraded
    analysis.raw_output = {
        "classification": classification_out.model_dump(),
        "scoring": scoring_out.model_dump(),
        "pricing": pricing
    }

    db.commit()
    db.refresh(analysis)
    db.refresh(upload)
    return analysis
