import random
from django.utils import timezone
from datetime import timedelta


def generate_otp():
    return f"{random.randint(100000, 999999)}"


def otp_is_valid(user, otp, ttl_minutes=10):
    if not user.otp_code or not user.otp_created_at:
        return False
    if user.otp_code != otp:
        return False
    return timezone.now() - user.otp_created_at < timedelta(minutes=ttl_minutes)


def send_sms(phone, message):
    """
    Plug in your SMS provider here (Africa's Talking, Twilio, etc.).
    For dev, we log to console.
    """
    print(f"[SMS -> {phone}] {message}")
    return True