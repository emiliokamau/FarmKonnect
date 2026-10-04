#!/usr/bin/env python3
"""Cryptographic Credential Generator and Rotation Helper for FarmKonnect.
Generates strong keys for DJANGO_SECRET_KEY, DB_PASSWORD, and administrative access.
"""

import secrets
import string
import sys
from pathlib import Path


def generate_secret_key(length: int = 54) -> str:
    """Generate high-entropy Django SECRET_KEY."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
    return "".join(secrets.choice(chars) for _ in range(length))


def generate_db_password(length: int = 32) -> str:
    """Generate strong alphanumeric database password."""
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def generate_admin_password(length: int = 24) -> str:
    """Generate strong administrative password."""
    chars = string.ascii_letters + string.digits + "!@#$^&*"
    return "".join(secrets.choice(chars) for _ in range(length))


def main():
    secret_key = generate_secret_key()
    db_password = generate_db_password()
    admin_password = generate_admin_password()

    print("=" * 72)
    print("FARMKONNECT PRODUCTION CREDENTIAL ROTATION GENERATOR")
    print("Domain: farmkonnect.zirocreativeagency.co.ke")
    print("=" * 72)
    print()
    print("1. GENERATED DJANGO_SECRET_KEY (54 chars, high-entropy):")
    print(f"   {secret_key}")
    print()
    print("2. GENERATED DATABASE PASSWORD (PostgreSQL 'farmkonnect'):")
    print(f"   {db_password}")
    print()
    print("3. GENERATED ADMIN TEMPORARY PASSWORD:")
    print(f"   {admin_password}")
    print()
    print("=" * 72)
    print("PRODUCTION .env TEMPLATE:")
    print("=" * 72)

    env_content = f"""# ==============================================================================
# FarmKonnect Production Environment Configuration
# Domain: https://farmkonnect.zirocreativeagency.co.ke
# ==============================================================================

# Core Django Settings
DJANGO_DEBUG=False
DJANGO_SECRET_KEY={secret_key}

# PostgreSQL Database Configuration
DB_NAME=farmkonnect
DB_USER=farmkonnect
DB_PASSWORD={db_password}
DB_HOST=127.0.0.1
DB_PORT=5432

# Redis & Channels Configuration
REDIS_URL=redis://127.0.0.1:6379/0

# TextSMS Kenya Production Gateway
TEXTSMS_API_KEY=YOUR_ROTATED_TEXTSMS_API_KEY
TEXTSMS_PARTNER_ID=YOUR_ROTATED_TEXTSMS_PARTNER_ID
TEXTSMS_SHORTCODE=FarmKonnect
TEXTSMS_API_DOMAIN=sms.textsms.co.ke

# SMTP Email Configuration
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=admin@zirocreativeagency.co.ke
EMAIL_HOST_PASSWORD=YOUR_ROTATED_APP_PASSWORD
DEFAULT_FROM_EMAIL=FarmKonnect <no-reply@farmkonnect.zirocreativeagency.co.ke>

# OTP Window Security (Minutes)
OTP_TTL_MINUTES=10

# AI Models (Google Gemini & ElevenLabs)
GEMINI_API_KEY=YOUR_ROTATED_GEMINI_API_KEY
GEMINI_MODEL=gemini-1.5-flash

ELEVENLABS_API_KEY=YOUR_ROTATED_ELEVENLABS_API_KEY
ELEVENLABS_VOICE_ID_EN=21m00Tcm4TlvDq8ikWAM
ELEVENLABS_VOICE_ID_SW=21m00Tcm4TlvDq8ikWAM
"""
    print(env_content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
