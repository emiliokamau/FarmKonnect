"""URL routing for KonnectAI REST API."""

from django.urls import path
from .views import (
    create_session_view,
    turn_view,
    session_detail_view,
    session_close_view,
    session_history_view,
)

urlpatterns = [
    path("sessions/", create_session_view, name="konnect-ai-sessions"),
    path("turn/", turn_view, name="konnect-ai-turn"),
    path("sessions/<int:pk>/", session_detail_view, name="konnect-ai-session-detail"),
    path("sessions/<int:pk>/close/", session_close_view, name="konnect-ai-session-close"),
    path("history/", session_history_view, name="konnect-ai-history"),
]
