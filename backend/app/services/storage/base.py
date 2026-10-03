from abc import ABC, abstractmethod
from typing import BinaryIO, Optional, Union
import os

class BaseStorageService(ABC):
    @abstractmethod
    def save_file(self, file_data: Union[bytes, BinaryIO], destination_path: str) -> str:
        """Saves file to storage and returns the storage_key"""
        pass

    @abstractmethod
    def get_file(self, storage_key: str) -> bytes:
        """Retrieves file bytes from storage"""
        pass

    @abstractmethod
    def get_file_path_or_url(self, storage_key: str) -> str:
        """Returns local path or signed URL for file access"""
        pass

    @abstractmethod
    def delete_file(self, storage_key: str) -> bool:
        """Deletes file from storage"""
        pass
