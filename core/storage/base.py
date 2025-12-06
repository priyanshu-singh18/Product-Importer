"""
Abstract Storage Backend Interface
Implements Strategy Pattern for swappable storage backends (S3, Local, Azure, etc.)
"""

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Abstract storage interface - swap S3/Azure/Local implementations"""

    @abstractmethod
    def generate_presigned_upload(self, key: str, expires_in: int = 3600) -> dict:
        """
        Generate presigned upload credentials for direct client upload.

        Returns:
            dict with 'url' and 'fields' for multipart form upload
        """
        pass

    @abstractmethod
    def download_file(self, key: str) -> bytes:
        """Download file content from storage"""
        pass

    @abstractmethod
    def file_exists(self, key: str) -> bool:
        """Check if file exists in storage"""
        pass

    @abstractmethod
    def delete_file(self, key: str) -> None:
        """Delete file from storage"""
        pass

    @abstractmethod
    def get_file_size(self, key: str) -> int:
        """Get file size in bytes"""
        pass
