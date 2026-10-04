"""Channels WebSocket tests for KonnectAI voice calling consumer."""

import base64
from unittest.mock import MagicMock, patch
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from rest_framework.authtoken.models import Token

from core_up.models import FarmerProfile
from konnect_ai.consumers import KonnectAIConsumer

User = get_user_model()


class VoiceConsumerTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="voice_farmer",
            phone="+254733445566",
            is_phone_verified=True,
        )
        self.profile = FarmerProfile.objects.create(
            user=self.user,
            full_name="Voice Farmer",
            county="Meru",
        )
        self.token = Token.objects.create(user=self.user)

    async def test_connect_without_token_rejected(self):
        """Connection without token should be closed / rejected."""
        communicator = WebsocketCommunicator(
            KonnectAIConsumer.as_asgi(),
            "/ws/konnect-ai/",
        )
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_connect_with_invalid_token_rejected(self):
        """Connection with invalid token should be rejected."""
        communicator = WebsocketCommunicator(
            KonnectAIConsumer.as_asgi(),
            "/ws/konnect-ai/?token=invalid_token_xyz",
        )
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_connect_with_valid_token_succeeds(self):
        """Connection with valid DRF token succeeds and receives session_ready."""
        communicator = WebsocketCommunicator(
            KonnectAIConsumer.as_asgi(),
            f"/ws/konnect-ai/?token={self.token.key}",
        )
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        init_msg = await communicator.receive_json_from(timeout=5)
        self.assertEqual(init_msg["type"], "session_ready")
        self.assertIn("session_id", init_msg)

        await communicator.disconnect()

    async def test_session_start_event(self):
        """Sending session_start returns session_ready confirmation."""
        communicator = WebsocketCommunicator(
            KonnectAIConsumer.as_asgi(),
            f"/ws/konnect-ai/?token={self.token.key}",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        # Consume initial greeting
        await communicator.receive_json_from(timeout=5)

        # Send session_start
        await communicator.send_json_to({"type": "session_start", "language": "en"})
        resp = await communicator.receive_json_from(timeout=5)
        self.assertEqual(resp["type"], "session_ready")

        await communicator.disconnect()

    async def test_audio_chunk_and_turn_completion(self):
        """Sending audio_chunk with commit triggers STT -> agent -> TTS -> turn_complete."""
        communicator = WebsocketCommunicator(
            KonnectAIConsumer.as_asgi(),
            f"/ws/konnect-ai/?token={self.token.key}",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        # Consume initial greeting
        await communicator.receive_json_from(timeout=5)

        # Mock dummy audio payload (100 bytes)
        fake_audio_b64 = base64.b64encode(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * 80).decode("ascii")

        await communicator.send_json_to({
            "type": "audio_chunk",
            "data": fake_audio_b64,
            "commit": True,
            "page": "dashboard",
        })

        # Collect event types until turn_complete
        received_types = []
        for _ in range(12):
            try:
                msg = await communicator.receive_json_from(timeout=5)
                received_types.append(msg.get("type"))
                if msg.get("type") == "turn_complete":
                    break
            except Exception:
                break

        self.assertIn("user_transcript", received_types)
        self.assertIn("intent", received_types)
        self.assertIn("reply_text", received_types)
        self.assertIn("audio_chunk", received_types)
        self.assertIn("turn_complete", received_types)

        await communicator.disconnect()

    async def test_barge_in_stops_playback(self):
        """Sending barge_in should immediately respond with playback_stopped."""
        communicator = WebsocketCommunicator(
            KonnectAIConsumer.as_asgi(),
            f"/ws/konnect-ai/?token={self.token.key}",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.receive_json_from(timeout=5)

        await communicator.send_json_to({"type": "barge_in"})
        msg = await communicator.receive_json_from(timeout=5)
        self.assertEqual(msg.get("type"), "playback_stopped")

        await communicator.disconnect()
