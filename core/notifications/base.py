"""
Abstract Progress Notifier Interface
Implements Strategy Pattern for swappable notification backends (WebSocket, SSE, Polling, etc.)
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class ProgressNotifier(ABC):
    """Abstract notifier interface - swap WebSocket/SSE/Polling implementations"""

    @abstractmethod
    def notify(self, job_id: UUID, data: dict[str, Any]) -> None:
        """
        Send progress notification for a job.

        Args:
            job_id: The import job UUID
            data: Progress data to send (status, stage, percent, etc.)
        """
        pass
