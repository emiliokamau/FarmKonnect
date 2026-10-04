from pathlib import Path

from django.apps import AppConfig


class CoreUpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core_up"
    path = Path(__file__).resolve().parent
