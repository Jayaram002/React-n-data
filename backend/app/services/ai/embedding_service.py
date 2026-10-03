from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.upload import Upload, UploadFile, DataType

class BaseEmbeddingService:
    def calculate_image_uniqueness(self, db: Session, phash: str, upload_id: Optional[int] = None) -> float:
        raise NotImplementedError

    def calculate_tabular_uniqueness(self, db: Session, column_names: List[str], signature_hash: str, upload_id: Optional[int] = None) -> float:
        raise NotImplementedError

class EmbeddingService(BaseEmbeddingService):
    @staticmethod
    def _hamming_distance(s1: str, s2: str) -> int:
        # Pad strings to same length if needed
        max_len = max(len(s1), len(s2))
        s1 = s1.ljust(max_len, '0')
        s2 = s2.ljust(max_len, '0')
        return sum(c1 != c2 for c1, c2 in zip(s1, s2))

    def calculate_image_uniqueness(self, db: Session, phash: str, upload_id: Optional[int] = None) -> float:
        if not phash:
            return 80.0 # Default neutral uniqueness

        # Query other image uploads
        query = db.query(UploadFile).filter(
            UploadFile.data_type == DataType.IMAGE,
            UploadFile.phash.isnot(None)
        )
        if upload_id:
            query = query.filter(UploadFile.upload_id != upload_id)

        existing_files = query.limit(100).all()
        if not existing_files:
            return 95.0 # High uniqueness for first upload in domain

        # Find minimum Hamming distance
        min_dist = 64
        for ef in existing_files:
            if ef.phash:
                dist = self._hamming_distance(phash, ef.phash)
                if dist < min_dist:
                    min_dist = dist

        # Map distance (0 to 16 hex chars) to 0-100 score
        # dist 0 -> 10, dist >= 12 -> 95
        score = min(98.0, max(15.0, (min_dist / 16.0) * 100.0))
        return round(score, 1)

    def calculate_tabular_uniqueness(
        self,
        db: Session,
        column_names: List[str],
        signature_hash: str,
        upload_id: Optional[int] = None
    ) -> float:
        if not column_names:
            return 80.0

        query = db.query(UploadFile).filter(
            UploadFile.data_type == DataType.TABULAR,
            UploadFile.column_schema.isnot(None)
        )
        if upload_id:
            query = query.filter(UploadFile.upload_id != upload_id)

        existing_files = query.limit(100).all()
        if not existing_files:
            return 95.0

        current_set = set(c.lower().strip() for c in column_names)
        max_jaccard = 0.0

        for ef in existing_files:
            schema = ef.column_schema or {}
            existing_cols = [c["name"] for c in schema.get("columns", []) if "name" in c]
            if existing_cols:
                other_set = set(c.lower().strip() for c in existing_cols)
                intersection = len(current_set.intersection(other_set))
                union = len(current_set.union(other_set))
                jaccard = intersection / union if union > 0 else 0.0
                if jaccard > max_jaccard:
                    max_jaccard = jaccard

        # High similarity (jaccard -> 1.0) means low uniqueness
        uniqueness = (1.0 - max_jaccard) * 100.0
        # Clamp between 20 and 98
        score = min(98.0, max(20.0, uniqueness))
        return round(score, 1)
