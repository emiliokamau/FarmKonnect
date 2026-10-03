# backend/__init__.py
"""FarmKonnect Django project package.

Ensures the Celery app is imported when Django starts so that ``celery -A farmkonnect``
works out‑of‑the‑box.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
