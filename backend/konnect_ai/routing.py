"""WebSocket routing for KonnectAI voice channels."""

from django.urls import path
from .consumers import KonnectAIConsumer

websocket_urlpatterns = [
    path("ws/konnect-ai/", KonnectAIConsumer.as_asgi()),
]
