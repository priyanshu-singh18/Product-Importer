"""
Local Filesystem Storage Backend (for development and testing)
"""

import os
from pathlib import Path
from .base import StorageBackend


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage for development"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, key: str) -> Path:
        """Convert storage key to full filesystem path"""
        full_path = self.base_path / key
        full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path

    def generate_presigned_upload(self, key: str, expires_in: int = 3600) -> dict:
        """
        For local storage, return a pseudo-presigned URL
        The upload will be handled by a Django view
        """
        return {
            "url": f"/api/storage/upload/",
            "fields": {
                "key": key,
            },
        }

    def download_file(self, key: str) -> bytes:
        """Read file from local filesystem"""
        full_path = self._get_full_path(key)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        return full_path.read_bytes()

    def file_exists(self, key: str) -> bool:
        """Check if file exists locally"""
        return self._get_full_path(key).exists()

    def delete_file(self, key: str) -> None:
        """Delete file from local filesystem"""
        full_path = self._get_full_path(key)
        if full_path.exists():
            full_path.unlink()

    def get_file_size(self, key: str) -> int:
        """Get file size in bytes"""
        full_path = self._get_full_path(key)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        return full_path.stat().st_size

    def save_upload(self, key: str, file_content: bytes) -> None:
        """Save uploaded file to local storage"""
        full_path = self._get_full_path(key)
        full_path.write_bytes(file_content)
