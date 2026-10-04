"""Channels WebSocket consumer for KonnectAI voice calling."""

from __future__ import annotations

import base64
import json
import logging
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework.authtoken.models import Token

from .agent import run_turn
from .elevenlabs import ElevenLabsClient
from .gemini import GeminiClient
from .models import ConversationSession

logger = logging.getLogger(__name__)


class KonnectAIConsumer(AsyncJsonWebsocketConsumer):
    """Voice WebSocket handler for KonnectAI voice calls."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.session = None
        self.language = "auto"
        self.audio_buffer = bytearray()
        self.elevenlabs = ElevenLabsClient()
        self.gemini = GeminiClient()
        self.is_interrupted = False

    async def connect(self):
        """Authenticate user using DRF Token passed in query string."""
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token_key = params.get("token", [None])[0]

        if not token_key:
            logger.warning("[KonnectAIConsumer] No token provided in WS query.")
            await self.close(code=4001)
            return

        user = await self._authenticate_token(token_key)
        if not user:
            logger.warning("[KonnectAIConsumer] Invalid token: %s", token_key)
            await self.close(code=4003)
            return

        self.user = user
        self.session = await self._create_session(user)

        await self.accept()
        await self.send_json({"type": "session_ready", "session_id": self.session.id})

    async def disconnect(self, close_code):
        """Clean up on disconnect."""
        if self.session:
            await self._close_session(self.session)

    async def receive_json(self, content: dict, **kwargs):
        """Process incoming client events."""
        msg_type = content.get("type")

        if msg_type in ("start", "session_start"):
            self.language = content.get("language", "auto")
            self.audio_buffer = bytearray()
            self.is_interrupted = False
            await self.send_json({"type": "session_ready", "session_id": self.session.id if self.session else None})

        elif msg_type in ("audio", "audio_chunk"):
            data_b64 = content.get("data", "")
            if data_b64:
                try:
                    chunk = base64.b64decode(data_b64)
                    self.audio_buffer.extend(chunk)
                except Exception as exc:
                    logger.warning("[KonnectAIConsumer] Audio decode error: %s", exc)
            if content.get("commit") or content.get("end_utterance"):
                await self._process_utterance(content.get("page", "dashboard"))

        elif msg_type == "end_utterance":
            await self._process_utterance(content.get("page", "dashboard"))

        elif msg_type in ("interrupt", "barge_in"):
            self.is_interrupted = True
            self.audio_buffer = bytearray()
            await self.send_json({"type": "playback_stopped"})

        elif msg_type in ("end", "session_end"):
            if self.session:
                await self._close_session(self.session)
            await self.close()

    async def _process_utterance(self, page: str = "dashboard"):
        """Run speech-to-text, agent dialogue turn, and text-to-speech."""
        if not self.audio_buffer:
            return

        raw_audio = bytes(self.audio_buffer)
        self.audio_buffer = bytearray()
        self.is_interrupted = False

        # 1. STT via ElevenLabs
        stt_lang = "sw" if self.language == "sw" else "en"
        transcription = await database_sync_to_async(self.elevenlabs.speech_to_text)(raw_audio, language=stt_lang)

        if not transcription:
            await self.send_json({"type": "error", "detail": "Could not understand audio."})
            return

        await self.send_json({
            "type": "user_transcript",
            "text": transcription,
            "lang": self.language,
        })
        await self.send_json({
            "type": "final_transcript",
            "text": transcription,
            "lang": self.language,
        })

        if self.is_interrupted:
            return

        # 2. Run Agent Turn in background database thread
        turn_result = await database_sync_to_async(run_turn)(
            session=self.session,
            user_text_local=transcription,
            lang=self.language,
            page=page,
            gemini_client=self.gemini,
        )

        # Notify intent
        await self.send_json({
            "type": "intent",
            "intent": turn_result["intent"],
        })

        # Notify tool executions
        for tc in turn_result.get("tool_calls", []):
            await self.send_json({
                "type": "tool_call",
                "name": tc["name"],
                "args": tc.get("args", {}),
            })
            await self.send_json({
                "type": "tool_result",
                "name": tc["name"],
                "ok": tc.get("ok", True),
                "summary": tc.get("summary", ""),
            })

        # Send text replies
        await self.send_json({"type": "reply_text", "text": turn_result["reply"]})
        await self.send_json({"type": "ai_text", "text": turn_result["reply_en"]})
        await self.send_json({"type": "ai_text_local", "text": turn_result["reply"]})

        if turn_result.get("sms_sent"):
            phone = getattr(self.user, "phone", "")
            await self.send_json({"type": "sms_sent", "to": phone, "ok": True})

        if self.is_interrupted:
            return

        # 3. TTS Synthesis
        tts_lang = "sw" if self.language == "sw" else "en"
        audio_b64 = await database_sync_to_async(self.elevenlabs.text_to_speech_base64)(
            turn_result["reply"],
            language=tts_lang,
        )

        if not self.is_interrupted:
            await self.send_json({
                "type": "audio_chunk",
                "data": audio_b64,
            })
            await self.send_json({
                "type": "audio_out",
                "data": audio_b64,
            })
            await self.send_json({"type": "turn_complete"})

    # ---------------- Sync-to-Async DB Helpers ----------------

    @database_sync_to_async
    def _authenticate_token(self, token_key: str):
        try:
            token = Token.objects.select_related("user").get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return None

    @database_sync_to_async
    def _create_session(self, user):
        return ConversationSession.objects.create(
            user=user,
            modality="voice",
            language=self.language,
        )

    @database_sync_to_async
    def _close_session(self, session):
        from django.utils import timezone
        if not session.ended_at:
            session.ended_at = timezone.now()
            session.save(update_fields=["ended_at"])
