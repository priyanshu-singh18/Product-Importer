"""
DRF Views for Webhook management
"""

import time
import json
import hmac
import hashlib
import requests
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Webhook, WebhookDelivery


class WebhookViewSet(viewsets.ModelViewSet):
    """
    Webhook CRUD operations.
    Includes test endpoint for delivery verification.
    """

    queryset = Webhook.objects.all()

    def list(self, request, *args, **kwargs):
        """List webhooks"""
        queryset = self.get_queryset()
        data = [self._serialize_webhook(w) for w in queryset]
        return Response({"results": data})

    def retrieve(self, request, *args, **kwargs):
        """Retrieve webhook"""
        instance = self.get_object()
        return Response(self._serialize_webhook(instance))

    def create(self, request, *args, **kwargs):
        """Create webhook"""
        try:
            webhook = Webhook.objects.create(**request.data)
            return Response(self._serialize_webhook(webhook), status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Update webhook"""
        instance = self.get_object()
        for key, value in request.data.items():
            setattr(instance, key, value)
        instance.save()
        return Response(self._serialize_webhook(instance))

    def destroy(self, request, *args, **kwargs):
        """Delete webhook"""
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _serialize_webhook(self, webhook):
        """Serialize webhook to dict"""
        return {
            "id": str(webhook.id),
            "name": webhook.name,
            "url": webhook.url,
            "event": webhook.event,
            "enabled": webhook.enabled,
            "created_at": webhook.created_at.isoformat(),
            "updated_at": webhook.updated_at.isoformat(),
        }

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        """
        Test webhook delivery.
        Sends a test payload and returns response status and timing.
        """
        webhook = self.get_object()

        # Test payload
        test_payload = {
            "event": "test",
            "message": "This is a test webhook delivery from Acme Product Importer",
            "timestamp": time.time(),
        }

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Acme-Webhook-Test/1.0",
        }

        # Add HMAC signature if secret exists
        payload_json = json.dumps(test_payload)
        if webhook.secret:
            signature = hmac.new(
                webhook.secret.encode(), payload_json.encode(), hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        # Send test request
        start_time = time.time()
        try:
            response = requests.post(webhook.url, data=payload_json, headers=headers, timeout=10)
            response_time_ms = int((time.time() - start_time) * 1000)

            # Track delivery
            WebhookDelivery.objects.create(
                webhook=webhook,
                event="test",
                payload=test_payload,
                response_status=response.status_code,
                response_body=response.text[:1000],
                response_time_ms=response_time_ms,
                success=200 <= response.status_code < 300,
            )

            return Response(
                {
                    "success": True,
                    "status_code": response.status_code,
                    "response_time_ms": response_time_ms,
                    "response_body": response.text[:500],
                }
            )

        except requests.exceptions.Timeout:
            response_time_ms = int((time.time() - start_time) * 1000)
            WebhookDelivery.objects.create(
                webhook=webhook,
                event="test",
                payload=test_payload,
                error_message="Request timeout",
                response_time_ms=response_time_ms,
                success=False,
            )
            return Response(
                {
                    "success": False,
                    "error": "Request timeout",
                    "response_time_ms": response_time_ms,
                },
                status=status.HTTP_408_REQUEST_TIMEOUT,
            )

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            WebhookDelivery.objects.create(
                webhook=webhook,
                event="test",
                payload=test_payload,
                error_message=str(e),
                response_time_ms=response_time_ms,
                success=False,
            )
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "response_time_ms": response_time_ms,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path="deliveries")
    def deliveries(self, request, pk=None):
        """Get delivery history for a webhook"""
        webhook = self.get_object()
        deliveries = WebhookDelivery.objects.filter(webhook=webhook).order_by("-created_at")[:50]
        data = [self._serialize_delivery(d) for d in deliveries]
        return Response({"results": data})

    def _serialize_delivery(self, delivery):
        """Serialize delivery to dict"""
        return {
            "id": delivery.id,
            "webhook_id": str(delivery.webhook_id),
            "webhook_name": delivery.webhook.name,
            "event": delivery.event,
            "response_status": delivery.response_status,
            "response_time_ms": delivery.response_time_ms,
            "success": delivery.success,
            "error_message": delivery.error_message,
            "created_at": delivery.created_at.isoformat(),
        }


class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view for webhook delivery history"""

    queryset = WebhookDelivery.objects.all().order_by("-created_at")

    def list(self, request, *args, **kwargs):
        """List deliveries"""
        queryset = self.get_queryset()[:100]
        data = []
        for delivery in queryset:
            data.append(
                {
                    "id": delivery.id,
                    "webhook_name": delivery.webhook.name,
                    "event": delivery.event,
                    "response_status": delivery.response_status,
                    "response_time_ms": delivery.response_time_ms,
                    "success": delivery.success,
                    "created_at": delivery.created_at.isoformat(),
                }
            )
        return Response({"results": data})
