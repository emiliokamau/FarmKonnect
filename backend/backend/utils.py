"""
Utility helpers for FarmKonnect:
  - OTP generation & validation
  - SMS sending via TextSMS Kenya (https://sms.textsms.co.ke)
  - Email sending via Django's configured email backend
  - A unified dispatcher that tries SMS then email (or email then SMS)
"""

import logging
import re
import requests
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# OTP
# ------------------------------------------------------------------
import random

def generate_otp():
    """Generate a 6-digit numeric OTP."""
    return f"{random.randint(100000, 999999)}"


def otp_is_valid(user, otp, ttl_minutes=None):
    """Return True if the user's OTP matches and hasn't expired."""
    if ttl_minutes is None:
        ttl_minutes = getattr(settings, "OTP_TTL_MINUTES", 10)

    if not user.otp_code or not user.otp_created_at:
        return False
    if str(user.otp_code) != str(otp).strip():
        return False
    return timezone.now() - user.otp_created_at < timedelta(minutes=ttl_minutes)


# ------------------------------------------------------------------
# Phone normalisation for TextSMS
#   TextSMS expects: 2547XXXXXXXX  (no +, no leading 0, country code first)
# ------------------------------------------------------------------
def normalize_phone_ke(phone: str) -> str:
    """Convert +254..., 07..., 254..., 01... to 2547XXXXXXX / 2541XXXXXXX."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)

    # 07XXXXXXXX or 01XXXXXXXX  ->  2547XXXXXXXX
    if digits.startswith("0") and len(digits) == 10:
        return "254" + digits[1:]

    # 2547XXXXXXXX (already correct)
    if digits.startswith("254") and len(digits) == 12:
        return digits

    # 7XXXXXXXX or 1XXXXXXXX (9 digits, no leading 0)
    if len(digits) == 9 and digits[0] in ("7", "1"):
        return "254" + digits

    # Fallback: return as-is (last resort)
    return digits


# ------------------------------------------------------------------
# SMS — TextSMS Kenya
# ------------------------------------------------------------------
def send_sms(phone: str, message: str) -> dict:
    """
    Send a single SMS via TextSMS Kenya.
    Returns a dict: {"ok": bool, "provider": "textsms", "raw": {...}}
    Logs and returns {"ok": False, ...} on any failure — never raises.
    """
    api_key = getattr(settings, "TEXTSMS_API_KEY", "")
    partner_id = getattr(settings, "TEXTSMS_PARTNER_ID", "")
    shortcode = getattr(settings, "TEXTSMS_SHORTCODE", "FarmKonnect")
    endpoint = getattr(
        settings,
        "TEXTSMS_ENDPOINT",
        "https://sms.textsms.co.ke/api/services/sendsms/",
    )

    mobile = normalize_phone_ke(phone)

    if not api_key or api_key == "PASTE_YOUR_API_KEY_HERE":
        logger.warning("[SMS skipped] TEXTSMS_API_KEY not configured. Would send to %s: %s", mobile, message)
        return {"ok": False, "provider": "textsms", "error": "API key not configured"}

    payload = {
        "apikey": api_key,
        "partnerID": partner_id,
        "message": message,
        "shortcode": shortcode,
        "mobile": mobile,
    }

    try:
        resp = requests.post(endpoint, json=payload, timeout=10)
        data = resp.json() if resp.content else {}
    except Exception as exc:
        logger.exception("TextSMS request failed: %s", exc)
        return {"ok": False, "provider": "textsms", "error": str(exc)}

    # Parse the response — TextSMS returns {"responses": [{"respose-code": 200, ...}]}
    ok = False
    try:
        responses = data.get("responses") or []
        if responses:
            code = int(responses[0].get("respose-code") or responses[0].get("response-code") or 0)
            ok = code == 200
    except (ValueError, TypeError, IndexError):
        ok = False

    if not ok:
        logger.warning("TextSMS responded with failure: %s", data)

    return {"ok": ok, "provider": "textsms", "raw": data}


# ------------------------------------------------------------------
# Email
# ------------------------------------------------------------------
def send_email(to_email: str, subject: str, body: str) -> dict:
    """
    Send a plain-text email using Django's configured email backend.
    Returns {"ok": bool, "provider": "email"} — never raises.
    """
    if not to_email:
        return {"ok": False, "provider": "email", "error": "no recipient"}

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[to_email],
            fail_silently=False,
        )
        return {"ok": True, "provider": "email"}
    except Exception as exc:
        logger.exception("Email send failed: %s", exc)
        return {"ok": False, "provider": "email", "error": str(exc)}


# ------------------------------------------------------------------
# Unified OTP dispatcher — tries SMS first, falls back to email
# ------------------------------------------------------------------
def send_otp(user, otp: str, purpose: str = "verification") -> dict:
    """
    Send an OTP to the user through SMS and/or email.

    Strategy:
      - If user has a phone → try SMS first.
      - If SMS fails (or phone missing) and user has an email → fall back to email.
      - If both missing → return error.

    Returns a summary dict so the view can include debug info.
    """
    message = f"Your FarmKonnect {purpose} code is {otp}. It expires in {getattr(settings, 'OTP_TTL_MINUTES', 10)} minutes."
    subject = "FarmKonnect verification code"

    result = {
        "sms": None,
        "email": None,
        "delivered": False,
        "channel": None,
    }

    # Try SMS first if we have a phone
    if user.phone:
        sms_result = send_sms(user.phone, message)
        result["sms"] = sms_result
        if sms_result.get("ok"):
            result["delivered"] = True
            result["channel"] = "sms"
            return result

    # Fall back to email
    if user.email:
        email_result = send_email(user.email, subject, message)
        result["email"] = email_result
        if email_result.get("ok"):
            result["delivered"] = True
            result["channel"] = "email"
            return result

    return result