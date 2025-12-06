"""
S3-Compatible Storage Backend (Works with AWS S3, Cloudflare R2, MinIO, etc.)
"""

import boto3
from botocore.exceptions import ClientError
from .base import StorageBackend


class S3StorageBackend(StorageBackend):
    """S3-compatible storage implementation for AWS S3, Cloudflare R2, etc."""

    def __init__(
        self,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        endpoint_url: str = None,
    ):
        self.bucket = bucket

        # Build client configuration
        client_config = {
            "service_name": "s3",
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": region,
        }

        # Only add endpoint_url if provided (for S3-compatible services like R2)
        # For standard AWS S3, endpoint_url should be None
        if endpoint_url:
            client_config["endpoint_url"] = endpoint_url

        self.client = boto3.client(**client_config)

    def generate_presigned_upload(self, key: str, expires_in: int = 3600) -> dict:
        """Generate presigned POST for direct browser upload"""
        try:
            response = self.client.generate_presigned_post(
                Bucket=self.bucket,
                Key=key,
                ExpiresIn=expires_in,
            )
            return response
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {e}")

    def download_file(self, key: str) -> bytes:
        """Download file from S3"""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            raise Exception(f"Failed to download file: {e}")

    def file_exists(self, key: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def delete_file(self, key: str) -> None:
        """Delete file from S3"""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            raise Exception(f"Failed to delete file: {e}")

    def get_file_size(self, key: str) -> int:
        """Get file size in bytes"""
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=key)
            return response["ContentLength"]
        except ClientError as e:
            raise Exception(f"Failed to get file size: {e}")
