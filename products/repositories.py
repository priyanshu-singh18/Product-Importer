"""
Repository Pattern implementations
Abstracts database operations for testability and flexibility
"""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID
from django.utils import timezone
from django.db.models import Q
from .dtos import ProductDTO, ImportJobDTO
from .models import Product, ImportJob


class ProductRepository(ABC):
    """Abstract repository - can swap Django ORM for SQLAlchemy/raw SQL"""

    @abstractmethod
    def bulk_upsert(
        self, products: list[ProductDTO], job_id: Optional[UUID] = None
    ) -> tuple[int, int]:
        """Bulk insert/update. Returns (created, updated)"""
        pass

    @abstractmethod
    def find_by_sku(self, sku: str) -> Optional[ProductDTO]:
        pass

    @abstractmethod
    def find_by_id(self, product_id: int) -> Optional[Product]:
        pass

    @abstractmethod
    def list_products(self, filters: dict, page: int, page_size: int) -> tuple[list[Product], int]:
        """Returns (products, total_count)"""
        pass

    @abstractmethod
    def create(self, product_dto: ProductDTO) -> Product:
        pass

    @abstractmethod
    def update(self, product_id: int, product_dto: ProductDTO) -> Product:
        pass

    @abstractmethod
    def delete(self, product_id: int) -> bool:
        pass

    @abstractmethod
    def delete_all(self) -> int:
        """Delete all products. Returns count."""
        pass


class DjangoProductRepository(ProductRepository):
    """Django ORM implementation of ProductRepository"""

    def bulk_upsert(
        self, products: list[ProductDTO], job_id: Optional[UUID] = None
    ) -> tuple[int, int]:
        """
        Bulk insert/update using Django 4.1+ bulk_create with update_conflicts.
        This is significantly faster than individual save() calls.
        Tracks which import job last created/updated each product.
        """
        if not products:
            return 0, 0

        seen = {}
        for dto in products:
            seen[dto.sku.lower()] = dto
        products = list(seen.values())

        # Check which SKUs already exist in database
        sku_list = [p.sku.lower() for p in products]
        existing = set(
            Product.objects.filter(sku_normalized__in=sku_list).values_list(
                "sku_normalized", flat=True
            )
        )

        # Build ORM objects
        now = timezone.now()
        orm_products = [
            Product(
                sku=dto.sku,
                sku_normalized=dto.sku.lower(),
                name=dto.name,
                description=dto.description,
                price=dto.price,
                active=dto.active,
                category_id=dto.category_id,
                last_import_job_id=job_id,
                updated_at=now,
            )
            for dto in products
        ]

        # Bulk upsert using Django 4.1+ feature
        update_fields = ["name", "description", "price", "active", "updated_at"]
        if job_id:
            update_fields.append("last_import_job_id")

        Product.objects.bulk_create(
            orm_products,
            update_conflicts=True,
            unique_fields=["sku_normalized"],
            update_fields=update_fields,
        )

        # Calculate created vs updated
        updated = len([p for p in orm_products if p.sku_normalized in existing])
        created = len(orm_products) - updated
        return created, updated

    def find_by_sku(self, sku: str) -> Optional[ProductDTO]:
        try:
            product = Product.objects.get(sku_normalized=sku.lower())
            return ProductDTO.model_validate(product)
        except Product.DoesNotExist:
            return None

    def find_by_id(self, product_id: int) -> Optional[Product]:
        try:
            return Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return None

    def list_products(self, filters: dict, page: int, page_size: int) -> tuple[list[Product], int]:
        """List products with filters and pagination"""
        queryset = Product.objects.select_related("category", "last_import_job").prefetch_related(
            "tags"
        )

        # Apply search filters (OR logic for sku/name)
        search_q = Q()
        if "sku" in filters and filters["sku"]:
            search_q |= Q(sku__icontains=filters["sku"])
        if "name" in filters and filters["name"]:
            search_q |= Q(name__icontains=filters["name"])
        if search_q:
            queryset = queryset.filter(search_q)

        # Apply other filters (AND logic)
        if "description" in filters and filters["description"]:
            queryset = queryset.filter(description__icontains=filters["description"])

        if "active" in filters and filters["active"] is not None:
            queryset = queryset.filter(active=filters["active"])

        if "category_id" in filters and filters["category_id"]:
            queryset = queryset.filter(category_id=filters["category_id"])

        if "import_job_id" in filters and filters["import_job_id"]:
            queryset = queryset.filter(last_import_job_id=filters["import_job_id"])

        total_count = queryset.count()

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        products = list(queryset[start:end])

        return products, total_count

    def create(self, product_dto: ProductDTO) -> Product:
        """Create a new product"""
        product = Product(
            sku=product_dto.sku,
            sku_normalized=product_dto.sku.lower(),
            name=product_dto.name,
            description=product_dto.description,
            price=product_dto.price,
            active=product_dto.active,
            category_id=product_dto.category_id,
        )
        product.save()
        return product

    def update(self, product_id: int, product_dto: ProductDTO) -> Product:
        """Update an existing product"""
        product = self.find_by_id(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        product.sku = product_dto.sku
        product.sku_normalized = product_dto.sku.lower()
        product.name = product_dto.name
        product.description = product_dto.description
        product.price = product_dto.price
        product.active = product_dto.active
        product.category_id = product_dto.category_id
        product.save()
        return product

    def delete(self, product_id: int) -> bool:
        """Delete a product"""
        try:
            product = Product.objects.get(id=product_id)
            product.delete()
            return True
        except Product.DoesNotExist:
            return False

    def delete_all(self) -> int:
        """Delete all products. Returns count."""
        count, _ = Product.objects.all().delete()
        return count


class ImportJobRepository(ABC):
    """Abstract repository for ImportJob operations"""

    @abstractmethod
    def create(self, user_id: Optional[int], filename: str, file_key: str) -> ImportJobDTO:
        pass

    @abstractmethod
    def get(self, job_id: UUID) -> ImportJobDTO:
        pass

    @abstractmethod
    def get_model(self, job_id: UUID) -> ImportJob:
        """Get the Django model instance"""
        pass

    @abstractmethod
    def update_status(self, job_id: UUID, status: str, stage: Optional[str] = None) -> None:
        pass

    @abstractmethod
    def update_progress(self, job_id: UUID, processed: int, created: int, updated: int) -> None:
        pass

    @abstractmethod
    def update_total_rows(self, job_id: UUID, total_rows: int) -> None:
        pass

    @abstractmethod
    def list_jobs(self, user_id: Optional[int] = None) -> list:
        """List jobs, optionally filtered by user_id"""
        pass


class DjangoImportJobRepository(ImportJobRepository):
    """Django ORM implementation of ImportJobRepository"""

    def create(self, user_id: Optional[int], filename: str, file_key: str) -> ImportJobDTO:
        """Create a new import job"""
        job = ImportJob.objects.create(user_id=user_id, filename=filename, file_key=file_key)
        return ImportJobDTO.from_model(job)

    def get(self, job_id: UUID) -> ImportJobDTO:
        """Get import job as DTO"""
        try:
            job = ImportJob.objects.get(id=job_id)
            return ImportJobDTO.from_model(job)
        except ImportJob.DoesNotExist:
            raise ValueError(f"ImportJob {job_id} not found")

    def get_model(self, job_id: UUID) -> ImportJob:
        """Get the Django model instance"""
        try:
            return ImportJob.objects.get(id=job_id)
        except ImportJob.DoesNotExist:
            raise ValueError(f"ImportJob {job_id} not found")

    def update_status(self, job_id: UUID, status: str, stage: Optional[str] = None) -> None:
        """Update job status and optionally stage"""
        job = self.get_model(job_id)
        job.status = status
        if stage:
            job.stage = stage
        if status == "running" and not job.started_at:
            job.started_at = timezone.now()
        if status in ["completed", "failed"]:
            job.completed_at = timezone.now()
        job.save()

    def update_progress(self, job_id: UUID, processed: int, created: int, updated: int) -> None:
        """Update progress counters"""
        ImportJob.objects.filter(id=job_id).update(
            processed_rows=processed, created_count=created, updated_count=updated
        )

    def update_total_rows(self, job_id: UUID, total_rows: int) -> None:
        """Update total rows count"""
        ImportJob.objects.filter(id=job_id).update(total_rows=total_rows)

    def list_jobs(self, user_id: Optional[int] = None) -> list:
        """List jobs, optionally filtered by user_id"""
        queryset = ImportJob.objects.all()
        if user_id is not None:
            queryset = queryset.filter(user_id=user_id)
        return list(queryset.order_by("-created_at"))
