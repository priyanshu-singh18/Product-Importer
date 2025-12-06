"""
Abstract Webhook Dispatcher Interface
Implements Adapter Pattern for swappable webhook backends
"""
from abc import ABC, abstractmethod
from typing import Any


class WebhookDispatcher(ABC):
    """Abstract dispatcher - can swap HTTP/Kafka/SQS implementations"""

    @abstractmethod
    def dispatch(self, event: str, payload: dict[str, Any]) -> None:
        """
        Dispatch webhook event.
        
        Args:
            event: Event type (e.g., 'import.completed')
            payload: Event payload data
        """
        pass

