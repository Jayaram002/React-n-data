import uuid
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.upload import Upload, UploadFile, UploadStatus, DataType, CategorySource
from app.models.audit import Flag, FlagStatus
from app.services.storage import get_storage_service
from app.services.security_scanner.scanner import SecurityScannerService
from app.services.prechecks.image import process_image
from app.services.prechecks.tabular import process_tabular

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
TABULAR_EXTENSIONS = {".csv", ".json", ".xlsx", ".xls"}

def determine_data_type(filename: str) -> DataType:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in IMAGE_EXTENSIONS:
        return DataType.IMAGE
    elif ext in TABULAR_EXTENSIONS:
        return DataType.TABULAR
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Allowed: Images (jpg, png, webp) or Tabular (csv, json, xlsx)")

def execute_upload_pipeline(
    db: Session,
    contributor_id: int,
    title: str,
    description: str,
    ai_training_allowed: bool,
    consent_version: str,
    filename: str,
    file_bytes: bytes,
    personal_data_status: str = "none",
    lawful_basis: Optional[str] = None,
    lawful_basis_note: Optional[str] = None,
    evidence_storage_key: Optional[str] = None
) -> Upload:
    # 1. Malware & Safety Scans
    malware_result = SecurityScannerService.scan_malware(file_bytes, filename)
    if not malware_result["clean"]:
        raise ValueError("File rejected: Malware detected by security scanner")

    data_type = determine_data_type(filename)
    storage_service = get_storage_service()

    # 2. Process Data Type & Compute Hashes / Schema
    if data_type == DataType.IMAGE:
        processed = process_image(file_bytes)
    else:
        processed = process_tabular(file_bytes, filename)

    # 3. Duplicate Detection across existing uploads
    is_duplicate = False
    dup_reason = ""

    if data_type == DataType.IMAGE and processed.get("phash"):
        dup_file = (
            db.query(UploadFile)
            .join(Upload, Upload.id == UploadFile.upload_id)
            .filter(
                UploadFile.phash == processed["phash"],
                Upload.contributor_id != contributor_id
            )
            .first()
        )
        if dup_file:
            is_duplicate = True
            dup_reason = f"Perceptual duplicate (pHash match) of upload #{dup_file.upload_id} from another contributor"
    elif data_type == DataType.TABULAR and processed.get("content_hash"):
        dup_file = (
            db.query(UploadFile)
            .join(Upload, Upload.id == UploadFile.upload_id)
            .filter(
                UploadFile.content_hash == processed["content_hash"],
                Upload.contributor_id != contributor_id
            )
            .first()
        )
        if dup_file:
            is_duplicate = True
            dup_reason = f"Exact duplicate content hash of upload #{dup_file.upload_id} from another contributor"

    # Check PII for Tabular
    has_pii = False
    pii_summary = ""
    if data_type == DataType.TABULAR and processed.get("pii_results", {}).get("pii_detected"):
        has_pii = True
        pii_summary = ", ".join(processed["pii_results"].get("pii_types", []))

    # Check Face / Plate detection for Images
    has_face_or_plate = False
    if data_type == DataType.IMAGE:
        lower_name = filename.lower()
        if any(term in lower_name for term in ["face", "plate", "license_plate", "portrait", "person", "selfie"]):
            has_face_or_plate = True

    # 4. Determine Initial Status under DPDP Act / Rules 2025
    initial_status = UploadStatus.UPLOADED
    if is_duplicate or has_pii or has_face_or_plate or personal_data_status == "contains_personal_data":
        initial_status = UploadStatus.FLAGGED

    # 5. Create Database Upload Record
    upload = Upload(
        contributor_id=contributor_id,
        title=title,
        description=description,
        status=initial_status,
        category_source=CategorySource.AI,
        ai_training_allowed=ai_training_allowed,
        consent_version=consent_version,
        personal_data_status=personal_data_status,
        lawful_basis=lawful_basis,
        lawful_basis_note=lawful_basis_note,
        evidence_storage_key=evidence_storage_key
    )
    db.add(upload)
    db.flush()

    # 6. Save Files in Storage
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    original_key = f"uploads/{upload.id}/original{ext}"
    storage_service.save_file(file_bytes, original_key)

    preview_ext = ".jpg" if data_type == DataType.IMAGE else ".json"
    preview_key = f"previews/{upload.id}/preview{preview_ext}"
    storage_service.save_file(processed["preview_bytes"], preview_key)

    # 7. Create UploadFile Record
    upload_file = UploadFile(
        upload_id=upload.id,
        data_type=data_type,
        storage_key=original_key,
        preview_key=preview_key,
        mime=processed["mime"],
        size=processed["size"],
        width=processed.get("width"),
        height=processed.get("height"),
        phash=processed.get("phash"),
        exif_stripped=processed.get("exif_stripped", False),
        row_count=processed.get("row_count"),
        column_schema=processed.get("column_schema"),
        content_hash=processed.get("content_hash"),
        signature_hash=processed.get("signature_hash")
    )
    db.add(upload_file)

    # 8. Create Flag records if duplicate, PII, face/plate, or personal data declaration
    if is_duplicate:
        flag = Flag(
            upload_id=upload.id,
            reason=dup_reason,
            source="system",
            status=FlagStatus.OPEN
        )
        db.add(flag)

    if has_pii or has_face_or_plate:
        hit_desc = pii_summary if has_pii else "face/plate visual identifier"
        if personal_data_status in ("none", "anonymized"):
            # Discrepancy flag
            flag = Flag(
                upload_id=upload.id,
                reason=f"Discrepancy: Contributor attested personal data is '{personal_data_status}', but {hit_desc} was detected.",
                source="system",
                status=FlagStatus.OPEN
            )
            db.add(flag)
        else:
            flag = Flag(
                upload_id=upload.id,
                reason=f"Personal data detected ({hit_desc}). Sent to admin moderation queue.",
                source="system",
                status=FlagStatus.OPEN
            )
            db.add(flag)

    if personal_data_status == "contains_personal_data":
        flag = Flag(
            upload_id=upload.id,
            reason=f"Contributor attested personal data with lawful basis '{lawful_basis or 'unspecified'}'. Moderation required before listing.",
            source="system",
            status=FlagStatus.OPEN
        )
        db.add(flag)

    db.commit()
    db.refresh(upload)
    return upload
