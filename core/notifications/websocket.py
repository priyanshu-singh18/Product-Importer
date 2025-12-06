"""
WebSocket Progress Notifier using Django Channels
"""

from typing import Any
from uuid import UUID
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .base import ProgressNotifier


class WebSocketNotifier(ProgressNotifier):
    """Send progress updates via Django Channels WebSocket"""

    def __init__(self):
        self.channel_layer = get_channel_layer()

    def notify(self, job_id: UUID, data: dict[str, Any]) -> None:
        """Broadcast progress to WebSocket group"""
        if not self.channel_layer:
            # Channels not configured, skip notification
            return

        group_name = f"import_job_{str(job_id)}"

        # Ensure all values are JSON serializable
        serialized_data = {
            "job_id": str(job_id),
            **{k: str(v) if isinstance(v, UUID) else v for k, v in data.items()},
        }

        async_to_sync(self.channel_layer.group_send)(
            group_name,
            {
                "type": "import_progress",
                "data": serialized_data,
            },
        )
