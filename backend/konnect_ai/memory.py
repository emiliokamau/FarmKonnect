"""Short-term conversation memory and transcript manager."""

from __future__ import annotations

from typing import List, Dict, Any
from django.utils import timezone
from .models import ConversationSession


class SessionMemory:
    """Manages short-term conversational context and transcript persistence."""

    def __init__(self, session: ConversationSession):
        self.session = session

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Return the current transcript list."""
        return self.session.transcript or []

    def get_last_turns(self, count: int = 3) -> List[Dict[str, Any]]:
        """Return the last `count` dialogue turns for context."""
        hist = self.history
        return hist[-count:] if hist else []

    def add_user_turn(self, text: str, lang: str = "en", original_text: str | None = None) -> None:
        """Record user speech or typed message."""
        transcript = list(self.history)
        turn = {
            "role": "user",
            "text": text,
            "original_text": original_text or text,
            "lang": lang,
            "timestamp": timezone.now().isoformat(),
        }
        transcript.append(turn)
        self.session.transcript = transcript
        self.session.save(update_fields=["transcript"])

    def add_ai_turn(
        self,
        text: str,
        lang: str = "en",
        text_local: str | None = None,
        intent: str = "GENERAL",
        tool_calls: List[Dict[str, Any]] | None = None,
    ) -> None:
        """Record AI response turn."""
        transcript = list(self.history)
        turn = {
            "role": "assistant",
            "text": text,
            "text_local": text_local or text,
            "lang": lang,
            "intent": intent,
            "tool_calls": tool_calls or [],
            "timestamp": timezone.now().isoformat(),
        }
        transcript.append(turn)
        self.session.transcript = transcript

        if tool_calls:
            existing_calls = list(self.session.tool_calls or [])
            existing_calls.extend(tool_calls)
            self.session.tool_calls = existing_calls
            self.session.save(update_fields=["transcript", "tool_calls"])
        else:
            self.session.save(update_fields=["transcript"])

    def mark_sms_sent(self) -> None:
        """Mark that an SMS confirmation was dispatched during this session."""
        self.session.sms_sent = True
        self.session.save(update_fields=["sms_sent"])

    def close(self) -> None:
        """Finalize the session timestamp."""
        if not self.session.ended_at:
            self.session.ended_at = timezone.now()
            self.session.save(update_fields=["ended_at"])
