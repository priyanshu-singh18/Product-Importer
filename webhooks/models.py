from django.db import models
from uuid import uuid4


class Webhook(models.Model):
    """
    Webhook configuration for event notifications.
    Supports HMAC signing for security.
    """

    EVENT_CHOICES = [
        ("import.completed", "Import Completed"),
        ("import.failed", "Import Failed"),
        ("product.created", "Product Created"),
        ("product.updated", "Product Updated"),
        ("product.deleted", "Product Deleted"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Friendly name for this webhook")
    url = models.URLField(help_text="Target URL for webhook delivery")
    event = models.CharField(max_length=64, choices=EVENT_CHOICES, db_index=True)
    secret = models.CharField(
        max_length=255,
        blank=True,
        help_text="Secret key for HMAC signature (optional)",
    )
    enabled = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event", "enabled"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.event}"


class WebhookDelivery(models.Model):
    """
    Track webhook delivery attempts for debugging and monitoring.
    Stores response status, body, and timing.
    """

    webhook = models.ForeignKey(
        Webhook, on_delete=models.CASCADE, related_name="deliveries"
    )
    event = models.CharField(max_length=64)
    payload = models.JSONField()
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(null=True, blank=True)
    response_time_ms = models.IntegerField(
        null=True, blank=True, help_text="Response time in milliseconds"
    )
    success = models.BooleanField(default=False, db_index=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Webhook deliveries"
        indexes = [
            models.Index(fields=["webhook", "-created_at"]),
            models.Index(fields=["success"]),
        ]

    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.webhook.name} - {status} - {self.created_at}"
