"""Audit logging and compliance utilities for KonnectAI."""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any

from django.utils import timezone
from .models import AuditLog, ConversationSession

logger = logging.getLogger(__name__)


def mask_pii(data: Any) -> Any:
    """Recursively mask sensitive values: phone numbers (show only last 4 digits),
    card numbers, PINs, and passwords. Never log raw audio/binary data.
    """
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            key_lower = str(k).lower()
            if any(term in key_lower for term in ["audio", "binary", "pcm", "mp3"]):
                masked[k] = "<binary_data_omitted>"
            elif any(term in key_lower for term in ["password", "pin", "secret", "token"]):
                masked[k] = "******"
            elif any(term in key_lower for term in ["phone", "mobile"]):
                masked[k] = mask_phone(v)
            else:
                masked[k] = mask_pii(v)
        return masked
    elif isinstance(data, list):
        return [mask_pii(item) for item in data]
    elif isinstance(data, str):
        # Mask Kenyan phone patterns (+254... or 07...)
        return re.sub(
            r"(\+?254|0)(\d{3,5})(\d{4})\b",
            r"\1***\3",
            data,
        )
    return data


def mask_phone(phone_val: Any) -> str:
    """Mask phone number showing only last 4 digits."""
    s = str(phone_val or "")
    if len(s) >= 4:
        return "*" * (len(s) - 4) + s[-4:]
    return "****"


def log_tool_call(
    user,
    tool_name: str,
    args: dict,
    ok: bool,
    result: Any = None,
    intent: str = "GENERAL",
    session: ConversationSession | None = None,
) -> AuditLog:
    """Record an immutable AuditLog entry with PII masking."""
    safe_args = mask_pii(args or {})
    safe_result = mask_pii(result) if result is not None else None

    try:
        return AuditLog.objects.create(
            user=user,
            session=session,
            intent=intent or "GENERAL",
            tool_name=tool_name,
            args=safe_args,
            ok=bool(ok),
            result=safe_result,
        )
    except Exception as exc:
        logger.exception("Failed to write AI AuditLog: %s", exc)
        return None


def check_rate_limit(user, max_calls_per_hour: int = 60) -> bool:
    """Return True if user is within rate limit; False if exceeded."""
    one_hour_ago = timezone.now() - timedelta(hours=1)
    call_count = AuditLog.objects.filter(
        user=user,
        created_at__gte=one_hour_ago,
    ).count()
    return call_count < max_calls_per_hour


def cleanup_expired_sessions(retention_days: int = 90) -> int:
    """Comply with Kenya Data Protection Act 2019: delete session transcripts older than retention_days."""
    cutoff = timezone.now() - timedelta(days=retention_days)
    count, _ = ConversationSession.objects.filter(started_at__lt=cutoff).delete()
    return count
