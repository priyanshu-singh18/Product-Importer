"""
Webhook event dispatcher helper functions
"""

from typing import Any
from .dispatchers.http import HTTPWebhookDispatcher


def dispatch_webhook_event(event: str, payload: dict[str, Any]) -> None:
    """
    Dispatch webhook event using configured dispatcher.
    Can be swapped for different implementations (Kafka, SQS, etc.)
    """
    dispatcher = HTTPWebhookDispatcher()
    dispatcher.dispatch(event, payload)
