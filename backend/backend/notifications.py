# backend/notifications.py
"""Push‑notification utilities.

For a production system you would integrate Firebase Cloud Messaging (FCM) using the
``firebase_admin`` SDK.  To keep the repository lightweight and avoid external
dependencies, this module provides a thin wrapper that logs the intended payload
instead of actually sending it.  The API mirrors the real implementation so the
code can be swapped with a real FCM client later.
"""

import logging
from typing import List

from django.conf import settings
from django.db import transaction

from .models import DeviceToken, User
from celery import shared_task

logger = logging.getLogger(__name__)


def _format_message(title: str, body: str) -> dict:
    """Return a dict representing an FCM message payload.

    The structure follows the format expected by ``firebase_admin.messaging``:
    ``{"notification": {"title": ..., "body": ...}}``.
    """
    return {"notification": {"title": title, "body": body}}


def _send_to_fcm(token: str, platform: str, message: dict) -> None:
    """Placeholder for the real FCM send call.

    In a real deployment you would call:
    ``messaging.send(message, token=token)`` after initializing the Firebase app.
    Here we simply log the action.
    """
    logger.info(
        "[FCM] Would send to %s token=%s payload=%s", platform, token, message
    )


def notify_user(user: User, title: str, body: str) -> None:
    """Send a push notification to all registered devices for *user*.

    The function is deliberately side‑effect free apart from logging – this makes
    it safe to run in unit tests.
    """
    tokens: List[DeviceToken] = list(user.device_tokens.all())
    if not tokens:
        logger.debug("User %s has no device tokens – skipping notification", user.username)
        return
    message = _format_message(title, body)
    for dt in tokens:
        _send_to_fcm(dt.token, dt.platform, message)


@shared_task(name="backend.notifications.send_price_spike")
def send_price_spike_notification(
    commodity_code: str, county_name: str, price: float, threshold: float
) -> None:
    """Notify all users in *county* when a price exceeds *threshold*.

    This is a simple demonstration task that could be scheduled after the ETL
    runs.  It looks up device tokens for users whose ``role`` is ``farmer`` and
    whose profile (if extended) matches the county – for now we just broadcast to
    all farmers.
    """
    if price < threshold:
        logger.debug(
            "Price %s for %s in %s below threshold %s – no notification", price, commodity_code, county_name, threshold
        )
        return

    title = f"Price Spike: {commodity_code} in {county_name}"
    body = f"Current price {price:.2f} exceeds your alert threshold of {threshold:.2f}."
    # Broadcast to all farmers (could be refined to county‑specific users)
    farmers = User.objects.filter(role="farmer")
    for farmer in farmers:
        notify_user(farmer, title, body)
