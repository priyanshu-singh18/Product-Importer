"""
Product domain models
"""

from django.db import models
from django.contrib.auth.models import User
from uuid import uuid4


class Category(models.Model):
    """Product category for organization"""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return str(self.name)


class Tag(models.Model):
    """Product tags for flexible categorization"""

    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return str(self.name)


class Product(models.Model):
    """
    Product model with case-insensitive SKU uniqueness.
    Uses sku_normalized for database-level uniqueness constraint.
    Tracks which import job last created/updated this product.
    """

    sku = models.CharField(max_length=255, db_index=True)
    sku_normalized = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Lowercase version of SKU for case-insensitive uniqueness",
    )
    name = models.TextField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    active = models.BooleanField(default=True, db_index=True)
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="products"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")
    last_import_job = models.ForeignKey(
        "ImportJob",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="imported_products",
        help_text="The import job that last created or updated this product",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sku_normalized"]),
            models.Index(fields=["active"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["last_import_job"]),
        ]

    def __str__(self):
        return f"{self.sku} - {self.name}"

    def save(self, *args, **kwargs):
        """Automatically set sku_normalized on save"""
        self.sku_normalized = str(self.sku).lower()
        super().save(*args, **kwargs)


class ImportJob(models.Model):
    """
    Import job tracking with presigned upload support.
    Status flow: pending_upload -> pending -> running -> completed/failed
    """

    STATUS_CHOICES = [
        ("pending_upload", "Pending Upload"),
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="import_jobs"
    )
    filename = models.TextField()
    file_key = models.TextField(help_text="Storage key for the uploaded file")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending_upload", db_index=True
    )
    stage = models.CharField(max_length=50, default="pending", help_text="Current processing stage")
    total_rows = models.IntegerField(null=True, blank=True)
    processed_rows = models.IntegerField(default=0)
    created_count = models.IntegerField(default=0)
    updated_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    error = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"ImportJob {self.id} - {self.status}"

    @property
    def percent_complete(self) -> float:
        """Calculate completion percentage"""
        if not self.total_rows or self.total_rows == 0:
            return 0.0
        return round((self.processed_rows / self.total_rows) * 100, 1)


class ImportError(models.Model):
    """Track individual row errors during import for audit trail"""

    job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name="import_errors")
    row_number = models.IntegerField()
    sku = models.CharField(max_length=255, null=True, blank=True)
    error_message = models.TextField()
    raw_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["row_number"]
        indexes = [
            models.Index(fields=["job", "row_number"]),
        ]
