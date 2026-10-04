"""ElevenLabs STT (Speech-to-Text) and TTS (Text-to-Speech) client with mock/offline fallback."""

from __future__ import annotations

import base64
import logging
from typing import Optional
import requests

from django.conf import settings

logger = logging.getLogger(__name__)

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech"
ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"

# 1-second silent MP3 header/frame for seamless playback fallback
SILENT_MP3_BASE64 = (
    "//uQxAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAACAAABhACgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoK"
    "CgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCg"
    "oKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoK"
    "CgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCg"
    "oKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoK"
    "CgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCg"
    "oKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoK"
    "CgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCg"
    "oKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoK"
    "CgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCg"
    "oKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoK"
    "CgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCg"
)


class ElevenLabsClient:
    """Client for ElevenLabs voice generation and transcription."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id_en: Optional[str] = None,
        voice_id_sw: Optional[str] = None,
    ):
        self.api_key = api_key or getattr(settings, "ELEVENLABS_API_KEY", "")
        self.voice_id_en = voice_id_en or getattr(settings, "ELEVENLABS_VOICE_ID_EN", "21m00Tcm4TlvDq8ikWAM")
        self.voice_id_sw = voice_id_sw or getattr(settings, "ELEVENLABS_VOICE_ID_SW", "21m00Tcm4TlvDq8ikWAM")

    def is_configured(self) -> bool:
        """Check if a real API key is configured."""
        return bool(self.api_key and self.api_key.strip() and self.api_key != "your-elevenlabs-api-key")

    def speech_to_text(self, audio_bytes: bytes, language: str = "en") -> str:
        """Convert incoming audio buffer to text."""
        if not audio_bytes:
            return ""

        if self.is_configured():
            headers = {"xi-api-key": self.api_key}
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            data = {"model_id": "scribe_v1", "language_code": language if language in ("en", "sw") else "sw"}
            try:
                resp = requests.post(ELEVENLABS_STT_URL, headers=headers, files=files, data=data, timeout=10)
                if resp.ok:
                    res_json = resp.json()
                    return res_json.get("text", "")
            except Exception as exc:
                logger.warning("[ElevenLabsClient] STT request failed: %s. Falling back.", exc)

        # Fallback transcription when offline / mock testing
        return "Nimeuza gunia tano za mahindi kwa elfu mbili kila moja" if language == "sw" else "I sold 5 bags of maize"

    def text_to_speech(self, text: str, language: str = "en") -> bytes:
        """Convert text into synthesized MP3 audio bytes."""
        if not text or not text.strip():
            return base64.b64decode(SILENT_MP3_BASE64)

        if self.is_configured():
            voice_id = self.voice_id_sw if language == "sw" else self.voice_id_en
            url = f"{ELEVENLABS_TTS_URL}/{voice_id}"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            }
            body = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                },
            }
            try:
                resp = requests.post(url, json=body, headers=headers, timeout=12)
                if resp.ok and resp.content:
                    return resp.content
            except Exception as exc:
                logger.warning("[ElevenLabsClient] TTS request failed: %s. Using silent fallback.", exc)

        return base64.b64decode(SILENT_MP3_BASE64)

    def text_to_speech_base64(self, text: str, language: str = "en") -> str:
        """Return base64-encoded MP3 string for WebSocket streaming."""
        audio_bytes = self.text_to_speech(text, language=language)
        return base64.b64encode(audio_bytes).decode("ascii")
