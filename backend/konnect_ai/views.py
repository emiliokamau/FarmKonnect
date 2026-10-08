"""REST API views for KonnectAI session bootstrap, text turn execution, and history."""

from __future__ import annotations

import logging
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .agent import run_turn
from .audit import check_rate_limit
from .models import ConversationSession
from .serializers import (
    ConversationSessionSerializer,
    TurnRequestSerializer,
    TurnResponseSerializer,
)

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_session_view(request):
    """Bootstrap a new voice or text session."""
    modality = request.data.get("modality", "text")
    language = request.data.get("language", "auto")

    session = ConversationSession.objects.create(
        user=request.user,
        modality=modality,
        language=language,
    )

    host = request.get_host()
    ws_protocol = "wss" if request.is_secure() else "ws"
    ws_url = f"{ws_protocol}://{host}/ws/konnect-ai/"

    return Response(
        {
            "session_id": session.id,
            "ws_url": ws_url,
            "modality": session.modality,
            "language": session.language,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def turn_view(request):
    """Process a single text-based user turn."""
    if not check_rate_limit(request.user, max_calls_per_hour=60):
        return Response(
            {"detail": "Rate limit exceeded. Maximum 60 requests per hour."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    serializer = TurnRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    session_id = data.get("session_id")
    if session_id:
        session = get_object_or_404(ConversationSession, id=session_id, user=request.user)
    else:
        session = ConversationSession.objects.create(
            user=request.user,
            modality="text",
            language=data.get("language", "auto"),
        )

    turn_output = run_turn(
        session=session,
        user_text_local=data["text"],
        lang=data.get("language", "auto"),
        page=data.get("page", "dashboard"),
    )

    response_payload = {
        **turn_output,
        "session_id": session.id,
    }
    return Response(response_payload, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def session_detail_view(request, pk: int):
    """Retrieve full transcript and metadata for a specific session."""
    session = get_object_or_404(ConversationSession, id=pk, user=request.user)
    serializer = ConversationSessionSerializer(session)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def session_close_view(request, pk: int):
    """Close and finalize a conversation session."""
    session = get_object_or_404(ConversationSession, id=pk, user=request.user)
    if not session.ended_at:
        session.ended_at = timezone.now()
        session.save(update_fields=["ended_at"])
    return Response({"detail": "Session closed.", "session_id": session.id})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def session_history_view(request):
    """List historical conversation sessions belonging to the authenticated user."""
    paginator = PageNumberPagination()
    paginator.page_size = 15
    sessions = ConversationSession.objects.filter(user=request.user).order_by("-started_at")
    result_page = paginator.paginate_queryset(sessions, request)
    serializer = ConversationSessionSerializer(result_page, many=True)
    return paginator.get_paginated_response(serializer.data)
