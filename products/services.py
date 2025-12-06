"""
Service Layer - Business Logic
Implements Clean Architecture by keeping business logic separate from Django
"""

import csv
from io import StringIO
from uuid import UUID, uuid4
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Optional

from .dtos import (
    ProductDTO,
    ImportJobDTO,
    ImportResultDTO,
    PresignedUploadDTO,
    ImportProgressDTO,
)
from .repositories import ProductRepository, ImportJobRepository
from .models import ImportError as ImportErrorModel
from core.storage.base import StorageBackend
from core.notifications.base import ProgressNotifier


class ImportService:
    """
    Business logic for CSV imports - framework agnostic.
    Can be easily tested with mock dependencies.
    """

    def __init__(
        self,
        product_repo: ProductRepository,
        job_repo: ImportJobRepository,
        storage: StorageBackend,
        notifier: ProgressNotifier,
    ):
        self.product_repo = product_repo
        self.job_repo = job_repo
        self.storage = storage
        self.notifier = notifier

    def generate_upload_url(self, user_id: Optional[int], filename: str) -> PresignedUploadDTO:
        """
        Generate presigned upload URL for client to upload directly to storage.
        This bypasses Django for large file uploads, avoiding timeout issues.
        """
        job_id = uuid4()
        file_key = f"imports/{job_id}/{filename}"

        # Create job record with pending_upload status
        job = self.job_repo.create(user_id, filename, file_key)

        # Generate presigned URL from storage backend (S3/Local)
        presigned = self.storage.generate_presigned_upload(file_key)

        return PresignedUploadDTO(
            job_id=job.id,
            upload_url=presigned["url"],
            fields=presigned["fields"],
            expires_in=3600,
        )

    def complete_upload(self, job_id: UUID) -> ImportJobDTO:
        """
        Verify upload completed and mark job as ready for processing.
        Called by client after successful upload to storage.
        """
        # Verify file exists in storage
        job_model = self.job_repo.get_model(job_id)
        if not self.storage.file_exists(job_model.file_key):
            raise ValueError("File not found in storage")

        # Update status to pending (ready for processing)
        self.job_repo.update_status(job_id, "pending", stage="pending")

        return self.job_repo.get(job_id)

    def list_jobs(self, user_id: Optional[int] = None) -> list:
        """
        List import jobs. If user_id is provided, filter by user.
        If user_id is None (staff user), return all jobs.
        """
        return self.job_repo.list_jobs(user_id)

    def get_job(self, job_id: UUID):
        """Get a single import job by ID"""
        return self.job_repo.get_model(job_id)

    def process_import(self, job_id: UUID) -> ImportResultDTO:
        """
        Process CSV import - called by Celery worker.
        Implements chunking strategy for memory efficiency.
        """
        start_time = datetime.now()
        job_model = self.job_repo.get_model(job_id)

        try:
            # Update to running
            self.job_repo.update_status(job_id, "running", stage="downloading")
            self._broadcast_progress(job_model)

            # Download from storage
            content = self.storage.download_file(job_model.file_key)
            text_content = content.decode("utf-8")

            # Count rows for progress tracking
            lines = text_content.strip().split("\n")
            total_rows = len(lines) - 1  # Exclude header
            self.job_repo.update_total_rows(job_id, total_rows)

            # Update stage to importing
            self.job_repo.update_status(job_id, "running", stage="importing")
            job_model.refresh_from_db()
            self._broadcast_progress(job_model)

            # Process CSV in chunks
            reader = csv.DictReader(StringIO(text_content))
            chunk = []
            total_created = 0
            total_updated = 0
            total_errors = 0
            total_duplicates_in_csv = 0
            row_number = 1
            rows_processed = 0

            for row in reader:
                row_number += 1
                rows_processed += 1

                # Parse and validate with Pydantic
                try:
                    product_dto = self._parse_row_to_dto(row)
                    chunk.append(product_dto)
                except Exception as e:
                    self._log_error(job_model, row_number, row, [str(e)])
                    total_errors += 1
                    continue

                # Process chunk when full
                if len(chunk) >= 10000:
                    # Note: bulk_upsert deduplicates chunk internally
                    # So chunk might have 10k items but only 8k unique SKUs
                    chunk_size_before_dedup = len(chunk)
                    created, updated = self.product_repo.bulk_upsert(chunk, job_id=job_id)
                    total_created += created
                    total_updated += updated

                    # Track duplicates within CSV file
                    duplicates_in_chunk = chunk_size_before_dedup - (created + updated)
                    total_duplicates_in_csv += duplicates_in_chunk

                    # Update progress based on actual rows read from CSV
                    self.job_repo.update_progress(
                        job_id, rows_processed, total_created, total_updated
                    )
                    job_model.error_count = total_errors
                    job_model.save(update_fields=["error_count"])
                    job_model.refresh_from_db()
                    self._broadcast_progress(job_model)
                    chunk = []

            # Process remaining rows
            if chunk:
                chunk_size_before_dedup = len(chunk)
                created, updated = self.product_repo.bulk_upsert(chunk, job_id=job_id)
                total_created += created
                total_updated += updated

                duplicates_in_chunk = chunk_size_before_dedup - (created + updated)
                total_duplicates_in_csv += duplicates_in_chunk

            # Mark as completed - use actual rows processed from CSV
            self.job_repo.update_progress(job_id, rows_processed, total_created, total_updated)
            job_model.error_count = total_errors
            job_model.save(update_fields=["error_count"])
            self.job_repo.update_status(job_id, "completed", stage="completed")
            job_model.refresh_from_db()
            self._broadcast_progress(job_model)

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()

            return ImportResultDTO(
                job_id=job_id,
                total_rows=total_rows,
                created_count=total_created,
                updated_count=total_updated,
                error_count=total_errors,
                duration_seconds=duration,
            )

        except Exception as e:
            # Mark as failed
            job_model.error = str(e)
            job_model.save(update_fields=["error"])
            self.job_repo.update_status(job_id, "failed", stage="failed")
            job_model.refresh_from_db()
            self._broadcast_progress(job_model)
            raise

    def _parse_row_to_dto(self, row: dict) -> ProductDTO:
        """Parse CSV row to ProductDTO with validation"""
        # Validate SKU
        if not row.get("sku") or not str(row["sku"]).strip():
            raise ValueError("SKU is required")

        sku = str(row["sku"]).strip()
        if len(sku) > 255:
            raise ValueError("SKU exceeds maximum length of 255 characters")

        price = None
        if row.get("price") and str(row["price"]).strip():
            try:
                price = Decimal(str(row["price"]).strip())
                if price < 0:
                    raise ValueError(f"Price must be positive: {price}")
            except (InvalidOperation, ValueError):
                raise ValueError(f"Invalid price: {row.get('price')}")

        return ProductDTO(
            sku=sku,
            name=row.get("name", ""),
            description=row.get("description", ""),
            price=price,
            active=True,
        )

    def _broadcast_progress(self, job_model) -> None:
        """Broadcast progress update via notifier (WebSocket/SSE)"""
        progress = ImportProgressDTO(
            job_id=job_model.id,
            status=job_model.status,
            stage=job_model.stage,
            processed_rows=job_model.processed_rows,
            total_rows=job_model.total_rows,
            percent=job_model.percent_complete,
            created_count=job_model.created_count,
            updated_count=job_model.updated_count,
        )
        self.notifier.notify(job_model.id, progress.model_dump(mode="json"))

    def _log_error(self, job_model, row_number: int, row: dict, errors: list[str]):
        """Log import error for audit trail"""
        ImportErrorModel.objects.create(
            job=job_model,
            row_number=row_number,
            sku=row.get("sku", ""),
            error_message="; ".join(errors),
            raw_data=row,
        )


class ProductService:
    """Business logic for product management"""

    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo

    def list_products(self, filters: dict, page: int = 1, page_size: int = 50):
        """List products with filters and pagination"""
        return self.product_repo.list_products(filters, page, page_size)

    def get_product(self, product_id: int):
        """Get single product"""
        return self.product_repo.find_by_id(product_id)

    def create_product(self, product_dto: ProductDTO):
        """Create new product"""
        return self.product_repo.create(product_dto)

    def update_product(self, product_id: int, product_dto: ProductDTO):
        """Update existing product"""
        return self.product_repo.update(product_id, product_dto)

    def delete_product(self, product_id: int) -> bool:
        """Delete product"""
        return self.product_repo.delete(product_id)

    def bulk_delete_all(self) -> int:
        """Delete all products - protected operation"""
        return self.product_repo.delete_all()
