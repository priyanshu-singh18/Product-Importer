"""
DRF Views for Product CRUD and Import operations
Uses Service Layer for business logic (Clean Architecture)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from uuid import UUID

from .services import ProductService, ImportService
from .repositories import DjangoProductRepository, DjangoImportJobRepository
from .dtos import ProductDTO
from django.conf import settings


def get_storage_backend():
    """Get storage backend from settings - imports the factory function"""
    from acme_importer.settings import get_storage_backend as _get_storage_backend

    return _get_storage_backend()


def get_notifier():
    """Get progress notifier"""
    from core.notifications.websocket import WebSocketNotifier

    return WebSocketNotifier()


class ProductViewSet(viewsets.ModelViewSet):
    """
    Product CRUD with filters and pagination.
    Uses ProductService for business logic.
    """

    pagination_class = PageNumberPagination

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = ProductService(DjangoProductRepository())

    def list(self, request, *args, **kwargs):
        """List products with filters"""
        filters = self._build_filters(request)
        page_number = int(request.query_params.get("page", 1))
        page_size = int(
            request.query_params.get("page_size", self.pagination_class.page_size or 50)
        )

        products, total_count = self.service.list_products(filters, page_number, page_size)
        data = [self._serialize_product(p) for p in products]

        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size

        return Response(
            {
                "count": total_count,
                "next": page_number < total_pages,
                "previous": page_number > 1,
                "results": data,
            }
        )

    def retrieve(self, request, *args, **kwargs):
        """Retrieve single product"""
        product = self.service.get_product(int(kwargs["pk"]))
        if not product:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(self._serialize_product(product))

    def create(self, request, *args, **kwargs):
        """Create product"""
        try:
            dto = ProductDTO(**request.data)
            product = self.service.create_product(dto)
            return Response(self._serialize_product(product), status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Update product"""
        try:
            dto = ProductDTO(**request.data)
            product = self.service.update_product(int(kwargs["pk"]), dto)
            return Response(self._serialize_product(product))
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Delete product"""
        success = self.service.delete_product(int(kwargs["pk"]))
        if success:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    def _build_filters(self, request):
        """Build filters dict from query params"""
        filters = {}

        sku = request.query_params.get("sku")
        if sku:
            filters["sku"] = sku

        name = request.query_params.get("name")
        if name:
            filters["name"] = name

        description = request.query_params.get("description")
        if description:
            filters["description"] = description

        active = request.query_params.get("active")
        if active is not None:
            filters["active"] = active.lower() == "true"

        category_id = request.query_params.get("category_id")
        if category_id:
            filters["category_id"] = category_id

        import_job_id = request.query_params.get("import_job_id")
        if import_job_id:
            filters["import_job_id"] = import_job_id

        return filters

    def _serialize_product(self, product):
        """Serialize product to dict"""
        return {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "description": product.description,
            "price": str(product.price) if product.price else None,
            "active": product.active,
            "category_id": product.category_id,
            "category": (
                {"id": product.category.id, "name": product.category.name}
                if product.category
                else None
            ),
            "tags": [{"id": tag.id, "name": tag.name} for tag in product.tags.all()],
            "last_import_job": (
                {
                    "id": str(product.last_import_job.id),
                    "filename": product.last_import_job.filename,
                    "created_at": product.last_import_job.created_at.isoformat(),
                }
                if product.last_import_job
                else None
            ),
            "created_at": product.created_at.isoformat(),
            "updated_at": product.updated_at.isoformat(),
        }

    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request):
        """
        Delete all products (protected operation).
        Requires confirmation header: X-Confirm-Delete: DELETE
        """
        confirmation = request.headers.get("X-Confirm-Delete")
        if confirmation != "DELETE":
            return Response(
                {"error": "Confirmation required. Send header: X-Confirm-Delete: DELETE"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        count = self.service.bulk_delete_all()
        return Response({"deleted": count}, status=status.HTTP_200_OK)


class ImportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Import job management.
    Uses ImportService with dependency injection.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = None  # Will be initialized per request

    def _get_service(self):
        """Get service instance with dependencies"""
        if not self.service:
            self.service = ImportService(
                product_repo=DjangoProductRepository(),
                job_repo=DjangoImportJobRepository(),
                storage=get_storage_backend(),
                notifier=get_notifier(),
            )
        return self.service

    def list(self, request, *args, **kwargs):
        """List import jobs"""
        service = self._get_service()
        jobs = service.list_jobs(user_id=None)  # Show all jobs (no auth)
        data = [self._serialize_job(j) for j in jobs]
        return Response({"results": data})

    def retrieve(self, request, *args, **kwargs):
        """Get import job details"""
        service = self._get_service()
        try:
            job = service.get_job(UUID(kwargs["pk"]))
            return Response(self._serialize_job(job))
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def _serialize_job(self, job):
        """Serialize import job"""
        return {
            "id": str(job.id),
            "filename": job.filename,
            "status": job.status,
            "stage": job.stage,
            "total_rows": job.total_rows,
            "processed_rows": job.processed_rows,
            "created_count": job.created_count,
            "updated_count": job.updated_count,
            "error_count": job.error_count,
            "percent": job.percent_complete,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

    @action(detail=False, methods=["post"], url_path="presign")
    def presign(self, request):
        """
        Generate presigned upload URL for direct client upload.
        Implements production-ready upload strategy.
        """
        filename = request.data.get("filename", "import.csv")

        service = self._get_service()

        result = service.generate_upload_url(
            user_id=None,  # No authentication required
            filename=filename,
        )

        return Response(
            {
                "job_id": str(result.job_id),
                "upload_url": result.upload_url,
                "fields": result.fields,
                "expires_in": result.expires_in,
            }
        )

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):  # noqa: ARG002
        """
        Mark upload as complete and enqueue processing.
        Called by client after successful upload.
        """
        service = self._get_service()

        try:
            job = service.complete_upload(UUID(pk))
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Enqueue Celery task
        from .tasks import process_csv_import_task

        process_csv_import_task.delay(str(job.id))

        return Response(
            {
                "job_id": str(job.id),
                "status": job.status,
                "ws_url": f"/ws/import/{job.id}/",
            }
        )

    @action(detail=True, methods=["get"], url_path="errors")
    def get_errors(self, request, pk=None):
        """
        Get validation errors for a specific import job.
        """
        from .models import ImportError

        try:
            errors = ImportError.objects.filter(job_id=UUID(pk)).order_by("row_number")[:100]
            data = [
                {
                    "row_number": err.row_number,
                    "sku": err.sku,
                    "error_message": err.error_message,
                    "raw_data": err.raw_data,
                }
                for err in errors
            ]
            return Response({"errors": data, "total": errors.count()})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["delete"], url_path="delete")
    def delete_job(self, request, pk=None):
        """
        Delete an import job (only for failed, pending, or pending_upload status).
        """
        from .models import ImportJob

        try:
            job = ImportJob.objects.get(id=UUID(pk))

            # Only allow deletion of non-active jobs
            if job.status in ["running"]:
                return Response(
                    {"error": "Cannot delete a running import job"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            job.delete()
            return Response(
                {"message": "Import job deleted successfully"}, status=status.HTTP_200_OK
            )
        except ImportJob.DoesNotExist:
            return Response({"error": "Import job not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="products")
    def get_products(self, request, pk=None):
        """
        Get products imported/updated by this specific job with pagination and search.
        Supports: search (sku/name), page, page_size
        """
        from .models import Product

        try:
            # Get pagination parameters
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
            search = request.query_params.get("search", "").strip()

            # Base query - products from this import job
            queryset = Product.objects.filter(last_import_job_id=UUID(pk))
            queryset = queryset.select_related("category", "last_import_job").prefetch_related(
                "tags"
            )

            # Search filter (SKU or Name)
            if search:
                from django.db.models import Q

                queryset = queryset.filter(Q(sku__icontains=search) | Q(name__icontains=search))

            # Get total count
            total_count = queryset.count()

            # Pagination
            start = (page - 1) * page_size
            end = start + page_size
            products = queryset[start:end]

            # Serialize products (reuse ProductViewSet's serializer)
            product_viewset = ProductViewSet()
            data = [product_viewset._serialize_product(p) for p in products]

            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

            return Response(
                {
                    "count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "next": page < total_pages,
                    "previous": page > 1,
                    "results": data,
                }
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def local_storage_upload(request):
    """
    Handle local storage uploads (for development).
    This endpoint is only used when STORAGE_BACKEND=local.
    """
    if settings.STORAGE_BACKEND != "local":
        return Response(
            {"error": "This endpoint is only available in local storage mode"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    key = request.data.get("key")
    file = request.FILES.get("file")

    if not key or not file:
        return Response({"error": "Missing key or file"}, status=status.HTTP_400_BAD_REQUEST)

    # Save file to local storage
    from core.storage.local import LocalStorageBackend

    storage = LocalStorageBackend(str(settings.MEDIA_ROOT))
    storage.save_upload(key, file.read())

    return Response({"status": "success", "key": key})
