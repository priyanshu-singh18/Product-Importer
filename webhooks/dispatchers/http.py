"""
HTTP Webhook Dispatcher with HMAC signing
"""
import time
import hmac
import hashlib
import json
import requests
from typing import Any
from celery import shared_task

from .base import WebhookDispatcher
from ..models import Webhook, WebhookDelivery


class HTTPWebhookDispatcher(WebhookDispatcher):
    """HTTP POST webhook dispatcher with HMAC signing and delivery tracking"""

    def dispatch(self, event: str, payload: dict[str, Any]) -> None:
        """
        Dispatch webhook to all enabled webhooks for this event.
        Sends asynchronously via Celery.
        """
        webhooks = Webhook.objects.filter(event=event, enabled=True)

        for webhook in webhooks:
            # Dispatch async via Celery
            send_webhook_task.delay(str(webhook.id), event, payload)


@shared_task(bind=True, max_retries=3)
def send_webhook_task(self, webhook_id: str, event: str, payload: dict):
    """
    Send webhook HTTP POST with HMAC signing.
    Tracks delivery for monitoring and debugging.
    """
    try:
        webhook = Webhook.objects.get(id=webhook_id)
    except Webhook.DoesNotExist:
        return

    # Prepare headers
    headers = {"Content-Type": "application/json", "User-Agent": "Acme-Webhook/1.0"}

    # Add HMAC signature if secret is configured
    payload_json = json.dumps(payload)
    if webhook.secret:
        signature = hmac.new(
            webhook.secret.encode(), payload_json.encode(), hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={signature}"

    # Send request and track timing
    start_time = time.time()
    delivery = WebhookDelivery(webhook=webhook, event=event, payload=payload)

    try:
        response = requests.post(
            webhook.url, data=payload_json, headers=headers, timeout=10
        )

        delivery.response_status = response.status_code
        delivery.response_body = response.text[:1000]  # Limit size
        delivery.response_time_ms = int((time.time() - start_time) * 1000)
        delivery.success = 200 <= response.status_code < 300

    except requests.exceptions.Timeout:
        delivery.error_message = "Request timeout"
        delivery.response_time_ms = int((time.time() - start_time) * 1000)
        delivery.success = False

    except Exception as e:
        delivery.error_message = str(e)
        delivery.response_time_ms = int((time.time() - start_time) * 1000)
        delivery.success = False

    finally:
        delivery.save()

    # Retry on failure if retries available
    if not delivery.success and self.request.retries < self.max_retries:
        raise self.retry(countdown=60 * (2**self.request.retries))

