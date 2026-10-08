"""Tests for KonnectAI REST API endpoints and rate limiting."""

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from core_up.models import FarmerProfile
from konnect_ai.models import AuditLog, ConversationSession

User = get_user_model()


class KonnectAIRestApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="api_farmer",
            phone="+254722112233",
            is_phone_verified=True,
        )
        self.profile = FarmerProfile.objects.create(
            user=self.user,
            full_name="API Farmer",
            county="Nyeri",
        )
        self.token = Token.objects.create(user=self.user)

    def test_unauthenticated_request_returns_401(self):
        """Unauthenticated requests must be rejected with 401 Unauthorized."""
        response = self.client.post(
            "/api/konnect-ai/turn/",
            {"text": "Hello, how are you?", "page": "dashboard"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(GEMINI_API_KEY="")
    def test_authenticated_turn_returns_200_and_payload(self):
        """Authenticated turn request returns 200 with reply and session_id."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.post(
            "/api/konnect-ai/turn/",
            {"text": "Hello, what tools are available?", "page": "dashboard"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("reply", response.data)
        self.assertIn("session_id", response.data)
        self.assertIn("intent", response.data)

    def test_create_session_endpoint(self):
        """POST /api/konnect-ai/sessions/ bootstraps a new session."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.post(
            "/api/konnect-ai/sessions/",
            {"modality": "voice", "language": "sw"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("session_id", response.data)
        self.assertIn("ws_url", response.data)
        self.assertEqual(response.data["modality"], "voice")

    def test_rate_limit_enforcement_60_calls_per_hour(self):
        """When 60 calls occur within the hour, 61st call returns 429."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        # Seed 60 AuditLog entries for this user
        session = ConversationSession.objects.create(user=self.user)
        logs = [
            AuditLog(
                user=self.user,
                session=session,
                intent="GENERAL",
                tool_name="list_farms",
                args={},
                ok=True,
            )
            for _ in range(60)
        ]
        AuditLog.objects.bulk_create(logs)

        # 61st call should trigger 429 Too Many Requests
        response = self.client.post(
            "/api/konnect-ai/turn/",
            {"text": "Another query after limit", "page": "dashboard"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("Rate limit exceeded", response.data.get("detail", ""))
