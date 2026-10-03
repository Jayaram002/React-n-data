import os
from pathlib import Path
from typing import BinaryIO, Union
from app.core.config import settings
from app.services.storage.base import BaseStorageService

class LocalStorageService(BaseStorageService):
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or settings.STORAGE_LOCAL_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_data: Union[bytes, BinaryIO], destination_path: str) -> str:
        # Normalize relative path to avoid path traversal
        clean_path = destination_path.lstrip("/\\")
        target_path = (self.base_dir / clean_path).resolve()
        
        # Security check: ensure target path is inside base_dir
        if not str(target_path).startswith(str(self.base_dir)):
            raise ValueError("Path traversal detected in destination path")

        target_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(file_data, bytes):
            with open(target_path, "wb") as f:
                f.write(file_data)
        else:
            with open(target_path, "wb") as f:
                f.write(file_data.read())

        return clean_path

    def get_file(self, storage_key: str) -> bytes:
        clean_path = storage_key.lstrip("/\\")
        target_path = (self.base_dir / clean_path).resolve()
        
        if not target_path.exists():
            raise FileNotFoundError(f"Storage key {storage_key} not found")

        with open(target_path, "rb") as f:
            return f.read()

    def get_file_path_or_url(self, storage_key: str) -> str:
        clean_path = storage_key.lstrip("/\\")
        target_path = (self.base_dir / clean_path).resolve()
        return str(target_path)

    def delete_file(self, storage_key: str) -> bool:
        clean_path = storage_key.lstrip("/\\")
        target_path = (self.base_dir / clean_path).resolve()
        if target_path.exists():
            target_path.unlink()
            return True
        return False
