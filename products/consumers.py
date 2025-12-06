"""
WebSocket consumers for real-time progress updates
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class ImportProgressConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for import progress updates.
    Clients connect to /ws/import/{job_id}/ to receive real-time progress.
    """

    async def connect(self):
        """Handle WebSocket connection"""
        self.job_id = self.scope["url_route"]["kwargs"]["job_id"]
        self.group_name = f"import_job_{self.job_id}"

        # Join group
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

        # Send initial connection confirmation
        await self.send(
            text_data=json.dumps(
                {"type": "connection", "status": "connected", "job_id": self.job_id}
            )
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle messages from WebSocket (not used, but required)"""
        pass

    async def import_progress(self, event):
        """
        Handle progress update from Celery worker.
        This method is called when a message is sent to the group.
        """
        # Send progress update to WebSocket
        await self.send(text_data=json.dumps(event["data"]))

