"""Backend app configuration."""

from django.apps import AppConfig


class BackendConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend"
    path = __import__("pathlib").Path(__file__).resolve().parent
