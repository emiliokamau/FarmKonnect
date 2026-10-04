"""Channels WebSocket consumer for KonnectAI voice calling.

Improvements added:
- Make TTS playback interruptible (barge-in): TTS synthesis/playback runs in a cancellable asyncio Task.
- Send immediate text replies to the client before starting TTS so the UI can show the assistant reply instantly.
- Cancel ongoing TTS when an "interrupt"/"barge_in" message arrives.
- Cancel TTS task on disconnect.
- Stream TTS as small base64 chunks (simulated by slicing the returned base64 payload) so the frontend can start playback earlier and handle partial audio.

Be careful: ElevenLabs client still returns a single base64 audio blob; slicing that blob only approximates streaming. For real streaming, integrate a streaming TTS API.
"""
from __future__ import annotations

import asyncio
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
    """Voice WebSocket handler for KonnectAI voice calls.

    This consumer now supports interruption (barge-in) during playback by
    running TTS synthesis/playback in an asyncio.Task that can be cancelled
    when the user sends an "interrupt" or "barge_in" event.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.session = None
        self.language = "auto"
        self.audio_buffer = bytearray()
        self.elevenlabs = ElevenLabsClient()
        self.gemini = GeminiClient()
        self.is_interrupted = False
        self._tts_task: asyncio.Task | None = None

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
        # Cancel any running TTS task
        if self._tts_task and not self._tts_task.done():
            self._tts_task.cancel()
            try:
                await self._tts_task
            except asyncio.CancelledError:
                pass
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
            # Mark interruption and cancel any ongoing TTS playback task
            self.is_interrupted = True
            self.audio_buffer = bytearray()

            # Cancel active TTS task so playback/synthesis stops
            if self._tts_task and not self._tts_task.done():
                self._tts_task.cancel()
                try:
                    await self._tts_task
                except asyncio.CancelledError:
                    pass
                finally:
                    self._tts_task = None

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

        # Send intermediate transcripts immediately so the UI shows them
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

        # Notify intent and tools immediately
        await self.send_json({
            "type": "intent",
            "intent": turn_result.get("intent"),
        })

        for tc in turn_result.get("tool_calls", []):
            await self.send_json({
                "type": "tool_call",
                "name": tc.get("name"),
                "args": tc.get("args", {}),
            })
            await self.send_json({
                "type": "tool_result",
                "name": tc.get("name"),
                "ok": tc.get("ok", True),
                "summary": tc.get("summary", ""),
            })

        # Send immediate text replies so UI can display before audio is ready
        reply_local = turn_result.get("reply") or ""
        reply_en = turn_result.get("reply_en") or ""
        await self.send_json({"type": "reply_text", "text": reply_local})
        await self.send_json({"type": "ai_text", "text": reply_en})
        await self.send_json({"type": "ai_text_local", "text": reply_local})

        if turn_result.get("sms_sent"):
            phone = getattr(self.user, "phone", "")
            await self.send_json({"type": "sms_sent", "to": phone, "ok": True})

        if self.is_interrupted:
            return

        # 3. Start TTS synthesis/playback in a cancellable background task
        tts_lang = "sw" if self.language == "sw" else "en"

        # Cancel any previous task (safety) before starting a new one
        if self._tts_task and not self._tts_task.done():
            self._tts_task.cancel()
            try:
                await self._tts_task
            except asyncio.CancelledError:
                pass
            finally:
                self._tts_task = None

        # Run the synth+stream task in background so we can still receive interrupts
        self._tts_task = asyncio.create_task(self._synthesize_and_stream_audio(reply_local, tts_lang))

    async def _synthesize_and_stream_audio(self, text: str, language: str):
        """Synthesize text to speech and stream it to the client in small chunks.

        This function is cancellable by cancelling the returned asyncio.Task.
        """
        try:
            # Synthesis is performed in a sync function; call it via database_sync_to_async to reuse the DB threadpool
            audio_b64 = await database_sync_to_async(self.elevenlabs.text_to_speech_base64)(text, language=language)
            if not audio_b64:
                await self.send_json({"type": "error", "detail": "TTS failed."})
                return

            # If a very large payload, stream it as smaller base64 slices so the frontend can begin playback early
            total_len = len(audio_b64)
            # Choose a reasonable slice size (characters of base64). Adjust as needed for performance.
            slice_size = 8192
            i = 0
            while i < total_len:
                if self.is_interrupted:
                    # If the user interrupted while streaming, stop sending more audio
                    await self.send_json({"type": "playback_stopped"})
                    return
                chunk = audio_b64[i : i + slice_size]
                await self.send_json({"type": "audio_chunk", "data": chunk})
                # Also send audio_out for compatibility with existing frontend handlers
                await self.send_json({"type": "audio_out", "data": chunk})
                i += slice_size
                # yield control briefly to allow interrupts to be processed
                await asyncio.sleep(0.01)

            # final marker
            await self.send_json({"type": "turn_complete"})

        except asyncio.CancelledError:
            # Task was cancelled due to user interrupt or disconnect
            logger.debug("[KonnectAIConsumer] TTS task cancelled (interrupted by user).")
            try:
                await self.send_json({"type": "playback_stopped"})
            except Exception:
                pass
            raise
        except Exception as exc:
            logger.exception("[KonnectAIConsumer] TTS synthesis/stream failed: %s", exc)
            await self.send_json({"type": "error", "detail": "TTS error"})
        finally:
            self._tts_task = None

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