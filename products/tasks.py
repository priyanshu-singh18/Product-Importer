"""
Celery tasks for asynchronous processing
"""

from uuid import UUID
from celery import shared_task

from .services import ImportService
from .repositories import DjangoProductRepository, DjangoImportJobRepository


def get_storage_backend():
    """Get storage backend from settings"""
    from acme_importer.settings import get_storage_backend as _get_storage_backend

    return _get_storage_backend()


def get_notifier():
    """Get progress notifier"""
    from core.notifications.websocket import WebSocketNotifier

    return WebSocketNotifier()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_csv_import_task(self, job_id: str):
    """
    Process CSV import asynchronously.
    Delegates to ImportService for business logic (Clean Architecture).

    Args:
        job_id: UUID string of the import job
    """
    service = ImportService(
        product_repo=DjangoProductRepository(),
        job_repo=DjangoImportJobRepository(),
        storage=get_storage_backend(),
        notifier=get_notifier(),
    )

    try:
        result = service.process_import(UUID(job_id))

        # Dispatch webhook on completion
        from core.signals import import_completed

        job = service.job_repo.get_model(UUID(job_id))
        import_completed.send(sender=service.__class__, job=job)

        # Could also trigger webhook dispatch here
        from webhooks.dispatcher import dispatch_webhook_event

        dispatch_webhook_event("import.completed", result.model_dump(mode="json"))

        return {
            "job_id": str(result.job_id),
            "created": result.created_count,
            "updated": result.updated_count,
            "errors": result.error_count,
        }

    except Exception as exc:
        # Log the error
        print(f"Import task failed: {exc}")

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
