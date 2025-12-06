"""
WebSocket URL routing for Django Channels
"""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/import/<str:job_id>/", consumers.ImportProgressConsumer.as_asgi()),
]

