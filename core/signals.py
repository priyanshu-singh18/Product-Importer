"""
Django Signals for extensibility
"""

from django.dispatch import Signal

# Import lifecycle signals
import_started = Signal()  # Provides: job
chunk_processed = Signal()  # Provides: job, chunk_number, chunk_size
import_completed = Signal()  # Provides: job
import_failed = Signal()  # Provides: job, error

# Product signals
product_created = Signal()  # Provides: product
product_updated = Signal()  # Provides: product
product_deleted = Signal()  # Provides: product_id
